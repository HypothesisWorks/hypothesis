from hypothesis.searchstrategy import nice_string, RandomWithSeed
from random import Random
from hypothesis.strategytable import StrategyTable
from hypothesis.descriptors import one_of, Just, OneOf
from abc import abstractmethod
from hypothesis.internal.specmapper import SpecificationMapper
import json
from hypothesis.internal.utils.hashitanyway import HashItAnyway
from hypothesis.internal.compat import text_type, binary_type, xrange


class Backend(object):
    """
    Interface class for storage systems. Simple key / multiple value store.
    """

    @abstractmethod
    def save(self, key, value):
        """
        Save a single value matching this key
        """

    @abstractmethod
    def fetch(self, key):
        """
        yield the values matching this key, ignoring duplicates
        """


class InMemoryBackend(Backend):
    """
    The default implementation.

    This backend simply saves the values in a dict. It's not very useful
    except in that it may speed up cases where the same example can fail
    multiple tests.
    """
    def __init__(self):
        self.data = {}

    def save(self, key, value):
        self.data.setdefault(key, set()).add(value)

    def fetch(self, key):
        for v in self.data.get(key, ()):
            yield v


class FormatTable(SpecificationMapper):
    """
    Mapper defining how data is serialized from a descriptor. Will handle
    anything it doesn't understand by just throwing it straight to JSON.
    """

    def __init__(self, strategy_table=None):
        super(FormatTable, self).__init__()
        self.strategy_table = strategy_table or StrategyTable.default()

    def missing_specification(self, descriptor):
        return generic_format


class Format(object):
    """
    Interface for converting objects to and from an object system suitable
    for converting to the JSON-with-bigints format that Python uses. Note:
    Does not actually serialize, only munges into a different shape.
    """

    @abstractmethod
    def to_json(self, value):
        """
        Turn this value into a JSON ready object
        """

    @abstractmethod
    def from_json(self, value):
        """
        Convert this value into a JSON ready object from the original type
        """


class GenericFormat(Format):
    """
    Trivial format that does no conversion. In the absence of anything
    more specific this will be used.
    """
    def to_json(self, value):
        return value

    def from_json(self, value):
        return value


generic_format = GenericFormat()


class ListFormat(Format):
    """
    Simply maps a child strategy over its elements as lists are natively
    supported
    """

    def __init__(self, child_format):
        self.child_format = child_format

    def to_json(self, value):
        return list(map(self.child_format.to_json, value))

    def from_json(self, value):
        return list(map(self.child_format.from_json, value))


def define_list_format(formats, descriptor):
    element_format = formats.specification_for(one_of(descriptor))
    if element_format is generic_format:
        return generic_format
    else:
        return ListFormat(element_format)

FormatTable.default().define_specification_for_instances(
    list, define_list_format)


class CollectionFormat(Format):
    """
    Round-trips a collection type via a list
    """

    def __init__(self, list_format, collection_type):
        self.list_format = list_format
        self.collection_type = collection_type

    def to_json(self, value):
        return self.list_format.to_json(list(value))

    def from_json(self, value):
        return self.collection_type(self.list_format.from_json(value))


def define_collection_format(formats, descriptor):
    return CollectionFormat(
        formats.specification_for(list(descriptor)),
        type(descriptor),
    )

FormatTable.default().define_specification_for_instances(
    set, define_collection_format)
FormatTable.default().define_specification_for_instances(
    frozenset, define_collection_format)


class ComplexFormat(Format):
    """
    Encodes complex numbers as a list [real, imaginary]
    """
    def to_json(self, c):
        return [c.real, c.imag]

    def from_json(self, c):
        return complex(*c)

FormatTable.default().define_specification_for(
    complex, lambda s, d: ComplexFormat())


class TextFormat(Format):
    """
    Text types which are guaranteed to be unicode clean are stored as normal
    JSON strings.
    """
    def to_json(self, c):
        return c

    def from_json(self, c):
        return text_type(c)

FormatTable.default().define_specification_for(
    text_type, lambda s, d: TextFormat()
)


class BinaryFormat(Format):
    """
    Binary types are base 64 encoded. Note that this includes str in python 2.7
    because it has no associated encoding. Use unicode objects in 2.7 if you
    care about human readable database formats.
    """

    def to_json(self, c):
        return c.encode('base64')

    def from_json(self, c):
        return c.decode('base64')

FormatTable.default().define_specification_for(
    binary_type, lambda s, d: BinaryFormat()
)


class RandomFormat(Format):
    """
    Stores one of hypothesis's RandomWithSeed types just by storing it as its
    seed value.
    """
    def to_json(self, c):
        return c.seed

    def from_json(self, c):
        return RandomWithSeed(c)

FormatTable.default().define_specification_for(
    Random, lambda s, d: RandomFormat()
)


class JustFormat(Format):
    """
    Just can only have a single value! We just represent this as a  null object
    and recover it as the value.
    """
    def __init__(self, value):
        self.value = value

    def to_json(self, c):
        return None

    def from_json(self, c):
        assert c is None
        return self.value


FormatTable.default().define_specification_for_instances(
    Just,
    lambda s, d: JustFormat(d.value)
)


class TupleFormat(Format):
    """
    Tuples are stored as lists of the correct length with each coordinate
    stored in its corresponding formats.
    """
    def __init__(self, tuple_formats):
        self.tuple_formats = tuple(tuple_formats)

    def to_json(self, value):
        return [
            f.to_json(v)
            for f, v in zip(self.tuple_formats, value)
        ]

    def from_json(self, value):
        return tuple(
            f.from_json(v)
            for f, v in zip(self.tuple_formats, value)
        )


FormatTable.default().define_specification_for_instances(
    tuple,
    lambda s, d: TupleFormat(
        s.specification_for(x)
        for x in d
    )
)


class FixedKeyDictFormat(Format):
    """
    Dicts are *not* stored as dicts. This is for a mix of reasons, but mostly
    that python supports a much greater range of keys than JSON does and we
    would have to find a way to encode them. Instead the keys are given an
    arbitrary but well defined order and the dict is serialized as per a tuple
    in that order.
    """
    def __init__(self, dict_of_formats):
        keys = tuple(
            sorted(
                dict_of_formats.keys(),
                key=lambda t: (t.__class__, repr(t)))
        )
        self.formats = tuple(
            (k, dict_of_formats[k]) for k in keys
        )

    def to_json(self, value):
        return [
            f.to_json(value[k])
            for k, f in self.formats
        ]

    def from_json(self, value):
        return {
            k: f.from_json(v)
            for (k, f), v in zip(self.formats, value)
        }


FormatTable.default().define_specification_for_instances(
    dict,
    lambda s, d: FixedKeyDictFormat({
        k: s.specification_for(v)
        for k, v in d.items()
    })
)


class OneOfFormat(Format):
    """
    OneOf stores its elements as pairs [integer tag, value] where the tag
    is the position of the first strategy in the list that could have produced
    it. There is some unavoidable ambiguity here where strategies can overlap
    but hopefully they have the property that on overlap their formats agree.
    This is the case for all the built in formats. You'll still get a result
    where it's not but it may result in some things being changed slightly.
    """
    def __init__(self, formats, strategies):
        assert len(formats) == len(strategies)
        self.formats = formats
        self.strategies = strategies

    def to_json(self, value):
        for i in xrange(len(self.formats)):
            if self.strategies[i].could_have_produced(value):
                return [i, self.formats[i].to_json(value)]
        raise ValueError("Invalid value %r for format" % (value,))

    def from_json(self, value):
        i, x = value
        return self.formats[i].from_json(x)


def define_one_of_format(format_table, descriptor):
    formats = [format_table.specification_for(v) for v in descriptor.elements]
    strategies = [
        format_table.strategy_table.specification_for(v)
        for v in descriptor.elements
    ]
    return OneOfFormat(formats, strategies)

FormatTable.default().define_specification_for_instances(
    OneOf, define_one_of_format
)


class Storage(object):
    """
    Handles saving and loading examples matching a particular descriptor.
    """
    def __init__(self, backend, descriptor, format, strategy):
        self.backend = backend
        self.descriptor = descriptor
        self.format = format
        self.strategy = strategy
        self.key = nice_string(descriptor)

    def save(self, value):
        if not self.strategy.could_have_produced(value):
            raise ValueError(
                "Argument %r does not match description %s" % (
                    value, self.key))
        converted = self.format.to_json(value)
        serialized = json.dumps(converted)
        self.backend.save(self.key, serialized)

    def fetch(self):
        for value in self.backend.fetch(self.key):
            deserialized = self.format.from_json(json.loads(value))
            if not self.strategy.could_have_produced(deserialized):
                raise ValueError(
                    "Value %r does not match description %s" % (
                        value, self.key))
            yield deserialized


class ExampleDatabase(object):
    """
    Object encapsulating all the things you need to get storage. Maps
    descriptors to storage for them.
    """
    def __init__(
        self,
        formats=None,
        backend=None,
    ):
        self.formats = formats or FormatTable.default()
        self.strategies = self.formats.strategy_table
        self.backend = backend or InMemoryBackend()
        self.storage_cache = {}

    def storage_for(self, descriptor):
        """
        Get a storage object corresponding to this descriptor. Will cache the
        result so that x.storage_for(d) is x.storage_for(d). You can rely on
        that behaviour.
        """
        key = HashItAnyway(descriptor)
        try:
            return self.storage_cache[key]
        except KeyError:
            pass

        result = Storage(
            descriptor=descriptor,
            backend=self.backend,
            format=self.formats.specification_for(descriptor),
            strategy=self.strategies.specification_for(descriptor),
        )
        self.storage_cache[key] = result
        return result
