"""
This module introduces the concept of *basic data*.

Basic data is:

    * Any unicode string (str in python 3, unicode in python 2)
    * Any data of type: float, bool, int, long (in python 2)
    * None
    * Any heterogenous list of basic data (including lists of lists, etc)

The goal of basic data is to provide a small set of primitives that a format
is responsible for marshalling and define formats for all other data in terms
of conversion to and from basic data.

A Converter is then responsible for converting data matching a particular
description to and from basic data. It essentially designs a schema for
representing values in a simpler form.

This uses a mechanism essentially identical to that of SearchStrategy for
mapping descriptors to converters.
"""


from hypothesis.searchstrategy import RandomWithSeed
from random import Random
from hypothesis.searchstrategy import nice_string
from hypothesis.strategytable import StrategyTable
from hypothesis.descriptors import one_of, Just, OneOf, SampledFrom
from abc import abstractmethod
from hypothesis.internal.specmapper import SpecificationMapper
from hypothesis.internal.compat import (
    text_type, binary_type, hrange, integer_types)
import base64


class WrongFormat(ValueError):

    """An exception indicating you have attempted to serialize a value that
    does not match the type described by this format."""
    pass


def check_matches(strategy, value):
    if not strategy.could_have_produced(value):
        raise WrongFormat('Value %r does not match description %s' % (
            value, nice_string(strategy.descriptor)
        ))


def check_type(typ, value):
    if not isinstance(value, typ):
        raise WrongFormat('Value %r is not an instance of %s' % (
            value, typ.__name__
        ))


class NotSerializeable(Exception):

    def __init__(self, descriptor):
        super(NotSerializeable, self).__init__(
            '%s does not describe a serializeable type' % (
                nice_string(descriptor),
            )
        )


def not_serializeable(s, d):
    raise NotSerializeable(d)


class ConverterTable(SpecificationMapper):

    """Mapper defining how data is serialized from a descriptor.

    Will handle anything it doesn't understand by just throwing it
    straight to JSON.

    """

    def __init__(self, strategy_table=None):
        super(ConverterTable, self).__init__()
        self.strategy_table = strategy_table or StrategyTable.default()

    def mark_not_serializeable(self, descriptor):
        self.define_specification_for(descriptor, not_serializeable)

    def missing_specification(self, descriptor):
        return not_serializeable(self, descriptor)


for basic_type in (
    type(None), float, text_type, bool
) + integer_types:
    ConverterTable.default().define_specification_for(
        basic_type,
        lambda s, d: GenericConverter(s.strategy_table.specification_for(d)))


class Converter(object):

    """
    Interface for converting objects to and from an object system suitable
    for converting to the JSON-with-bigints converter that Python uses. Note:
    Does not actually serialize, only munges into a different shape.
    """

    @abstractmethod  # pragma: no cover
    def to_json(self, value):
        """Turn this value into a JSON ready object."""

    @abstractmethod  # pragma: no cover
    def from_json(self, value):
        """Convert this value into a JSON ready object from the original
        type."""


class GenericConverter(Converter):

    """Trivial converter that does no conversion.

    In the absence of anything more specific this will be used.

    """

    def __init__(self, strategy):
        self.strategy = strategy

    def to_json(self, value):
        check_matches(self.strategy, value)
        return value

    def from_json(self, value):
        return value


class ListConverter(Converter):

    """Simply maps a child strategy over its elements as lists are natively
    supported."""

    def __init__(self, child_converter):
        self.child_converter = child_converter

    def to_json(self, value):
        check_type(list, value)
        return list(map(self.child_converter.to_json, value))

    def from_json(self, value):
        return list(map(self.child_converter.from_json, value))


def define_list_converter(converters, descriptor):
    element_converter = converters.specification_for(one_of(descriptor))
    if isinstance(element_converter, GenericConverter):
        return GenericConverter(
            converters.strategy_table.specification_for(descriptor))
    else:
        return ListConverter(element_converter)

ConverterTable.default().define_specification_for_instances(
    list, define_list_converter)


class CollectionConverter(Converter):

    """
    Round-trips a collection type via a list
    """

    def __init__(self, list_converter, collection_type):
        self.list_converter = list_converter
        self.collection_type = collection_type

    def to_json(self, value):
        check_type(self.collection_type, value)
        return self.list_converter.to_json(list(value))

    def from_json(self, value):
        return self.collection_type(self.list_converter.from_json(value))


def define_collection_converter(converters, descriptor):
    return CollectionConverter(
        converters.specification_for(list(descriptor)),
        type(descriptor),
    )

ConverterTable.default().define_specification_for_instances(
    set, define_collection_converter)
ConverterTable.default().define_specification_for_instances(
    frozenset, define_collection_converter)


class ComplexConverter(Converter):

    """Encodes complex numbers as a list [real, imaginary]"""

    def to_json(self, value):
        check_type(complex, value)
        return [value.real, value.imag]

    def from_json(self, c):
        return complex(*c)

ConverterTable.default().define_specification_for(
    complex, lambda s, d: ComplexConverter())


class TextConverter(Converter):

    """Text types which are guaranteed to be unicode clean are stored as normal
    JSON strings."""

    def to_json(self, c):
        check_type(text_type, c)
        return c

    def from_json(self, c):
        return text_type(c)

ConverterTable.default().define_specification_for(
    text_type, lambda s, d: TextConverter()
)


class BinaryConverter(Converter):

    """Binary types are base 64 encoded.

    Note that this includes str in python 2.7
    because it has no associated encoding. Use unicode objects in 2.7 if you
    care about human readable database converters.

    """

    def to_json(self, value):
        check_type(binary_type, value)
        return base64.b64encode(value).decode('utf-8')

    def from_json(self, data):
        return base64.b64decode(data.encode('utf-8'))

ConverterTable.default().define_specification_for(
    binary_type, lambda s, d: BinaryConverter()
)


class RandomConverter(Converter):

    """Stores one of hypothesis's RandomWithSeed types just by storing it as
    its seed value."""

    def to_json(self, value):
        check_type(RandomWithSeed, value)
        return value.seed

    def from_json(self, c):
        return RandomWithSeed(c)

ConverterTable.default().define_specification_for(
    Random, lambda s, d: RandomConverter()
)


class JustConverter(Converter):

    """Just can only have a single value!

    We just represent this as a  null object and recover it as the
    value.

    """

    def __init__(self, value):
        self.value = value

    def to_json(self, c):
        if c != self.value:
            raise WrongFormat('%r != %r' % (c, self.value))
        return None

    def from_json(self, c):
        assert c is None
        return self.value


ConverterTable.default().define_specification_for_instances(
    Just,
    lambda s, d: JustConverter(d.value)
)


class TupleConverter(Converter):

    """Tuples are stored as lists of the correct length with each coordinate
    stored in its corresponding converters."""

    def __init__(self, tuple_converters, tuple_type):
        self.tuple_type = tuple_type
        self.tuple_converters = tuple(tuple_converters)

    def to_json(self, value):
        check_type(self.tuple_type, value)
        if len(self.tuple_converters) == 1:
            return self.tuple_converters[0].to_json(value[0])
        return [
            f.to_json(v)
            for f, v in zip(self.tuple_converters, value)
        ]

    def from_json(self, value):
        if len(self.tuple_converters) == 1:
            return (self.tuple_converters[0].from_json(value),)
        return self.new_tuple(
            f.from_json(v)
            for f, v in zip(self.tuple_converters, value)
        )

    def new_tuple(self, value):
        value = tuple(value)
        if self.tuple_type == tuple:
            return value
        else:
            return self.tuple_type(*value)


ConverterTable.default().define_specification_for_instances(
    tuple,
    lambda s, d: TupleConverter(
        (s.specification_for(x) for x in d),
        type(d),
    )
)


class FixedKeyDictConverter(Converter):

    """
    Dicts are *not* stored as dicts. This is for a mix of reasons, but mostly
    that python supports a much greater range of keys than JSON does and we
    would have to find a way to encode them. Instead the keys are given an
    arbitrary but well defined order and the dict is serialized as per a tuple
    in that order.
    """

    def __init__(self, dict_of_converters):
        keys = tuple(
            sorted(
                dict_of_converters.keys(),
                key=lambda t: (t.__class__.__name__, repr(t)))
        )
        self.converters = tuple(
            (k, dict_of_converters[k]) for k in keys
        )

    def to_json(self, value):
        check_type(dict, value)
        return [
            f.to_json(value[k])
            for k, f in self.converters
        ]

    def from_json(self, value):
        return {
            k: f.from_json(v)
            for (k, f), v in zip(self.converters, value)
        }


ConverterTable.default().define_specification_for_instances(
    dict,
    lambda s, d: FixedKeyDictConverter({
        k: s.specification_for(v)
        for k, v in d.items()
    })
)


class OneOfConverter(Converter):

    """OneOf stores its elements as pairs [integer tag, value] where the tag is
    the position of the first strategy in the list that could have produced it.

    There is some unavoidable ambiguity here where strategies can
    overlap but hopefully they have the property that on overlap their
    converters agree. This is the case for all the built in converters.
    You'll still get a result where it's not but it may result in some
    things being changed slightly.

    """

    def __init__(self, converters, strategies):
        assert len(converters) == len(strategies)
        self.converters = converters
        self.strategies = strategies

    def to_json(self, value):
        for i in hrange(len(self.converters)):  # pragma: no branch
            if self.strategies[i].could_have_produced(value):
                return [i, self.converters[i].to_json(value)]
        raise WrongFormat('Value %r does not match any of %s' % (
            value, ', '.join(
                nice_string(s.descriptor) for s in self.strategies)))

    def from_json(self, value):
        i, x = value
        return self.converters[i].from_json(x)


def define_one_of_converter(converter_table, descriptor):
    converters = [
        converter_table.specification_for(v) for v in descriptor.elements]
    strategies = [
        converter_table.strategy_table.specification_for(v)
        for v in descriptor.elements
    ]
    return OneOfConverter(converters, strategies)

ConverterTable.default().define_specification_for_instances(
    OneOf, define_one_of_converter
)


class SampledFromConverter(Converter):

    """A SampledFrom instance is simply stored as an integer index into the
    list of values sampled from."""

    def __init__(self, choices):
        self.choices = tuple(choices)

    def to_json(self, value):
        try:
            return self.choices.index(value)
        except ValueError:
            raise WrongFormat('%r is not in %r' % (value, self.choices,))

    def from_json(self, value):
        return self.choices[value]


ConverterTable.default().define_specification_for_instances(
    SampledFrom, lambda s, d: SampledFromConverter(d.elements)
)
