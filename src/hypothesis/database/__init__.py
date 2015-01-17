from hypothesis.searchstrategy import nice_string
from abc import abstractmethod
import json
from hypothesis.internal.utils.hashitanyway import HashItAnyway
from hypothesis.database.format import FormatTable


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
