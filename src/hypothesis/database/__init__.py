from hypothesis.searchstrategy import nice_string
from hypothesis.internal.utils.hashitanyway import HashItAnyway
from hypothesis.database.converter import ConverterTable
from hypothesis.database.formats import JSONFormat
from hypothesis.database.backend import SQLiteBackend


class Storage(object):

    """Handles saving and loading examples matching a particular descriptor."""

    def __init__(self, backend, descriptor, converter, strategy, format):
        self.backend = backend
        self.descriptor = descriptor
        self.converter = converter
        self.format = format
        self.strategy = strategy
        self.key = nice_string(descriptor)

    def save(self, value):
        if not self.strategy.could_have_produced(value):
            raise ValueError(
                'Argument %r does not match description %s' % (
                    value, self.key))
        converted = self.converter.to_json(value)
        serialized = self.format.serialize_basic(converted)
        self.backend.save(self.key, serialized)

    def fetch(self):
        for data in self.backend.fetch(self.key):
            deserialized = self.converter.from_json(
                self.format.deserialize_data(data))
            if not self.strategy.could_have_produced(deserialized):
                raise ValueError(
                    'Value %r does not match description %s' % (
                        data, self.key))
            yield deserialized


class ExampleDatabase(object):

    """Object encapsulating all the things you need to get storage.

    Maps descriptors to storage for them.

    """

    def __init__(
        self,
        converters=None,
        backend=None,
        format=None,
    ):
        self.converters = converters or ConverterTable.default()
        self.strategies = self.converters.strategy_table
        self.backend = backend or SQLiteBackend()
        self.format = format or JSONFormat()
        if self.format.data_type() != self.backend.data_type():
            raise ValueError((
                'Inconsistent data types: format provides data of type %s '
                'but backend expects data of type %s' % (
                    self.format.data_type(), self.backend.data_type()
                )))
        self.storage_cache = {}

    def storage_for(self, descriptor):
        """Get a storage object corresponding to this descriptor.

        Will cache the result so that x.storage_for(d) is
        x.storage_for(d). You can rely on that behaviour.

        """
        key = HashItAnyway(descriptor)
        try:
            return self.storage_cache[key]
        except KeyError:
            pass

        result = Storage(
            descriptor=descriptor,
            backend=self.backend,
            format=self.format,
            converter=self.converters.specification_for(descriptor),
            strategy=self.strategies.specification_for(descriptor),
        )
        self.storage_cache[key] = result
        return result
