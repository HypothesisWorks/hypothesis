from hypothesis.searchstrategy import nice_string
from hypothesis.internal.utils.hashitanyway import HashItAnyway
from hypothesis.internal.tracker import Tracker
from hypothesis.database.converter import ConverterTable, BadData
from hypothesis.database.formats import JSONFormat
from hypothesis.database.backend import SQLiteBackend


class Storage(object):

    """Handles saving and loading examples matching a particular descriptor."""

    def __init__(
        self, backend, descriptor, converter, strategy, format,
        database
    ):
        self.database = database
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

        tracker = Tracker()

        def do_save(d, v):
            if tracker.track((d, v)) > 1:
                return
            s = self.database.storage_for(d)
            converted = s.converter.to_basic(v)
            serialized = s.format.serialize_basic(converted)
            s.backend.save(s.key, serialized)

            for d2, v2 in s.strategy.decompose(v):
                do_save(d2, v2)

        do_save(self.descriptor, value)

    def fetch(self):
        for data in self.backend.fetch(self.key):
            try:
                deserialized = self.converter.from_basic(
                    self.format.deserialize_data(data))
            except BadData:
                self.backend.delete(self.key, data)
                continue
            if not self.strategy.could_have_produced(deserialized):
                self.backend.delete(self.key, data)
            else:
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
            database=self,
            backend=self.backend,
            format=self.format,
            converter=self.converters.specification_for(descriptor),
            strategy=self.strategies.specification_for(descriptor),
        )
        self.storage_cache[key] = result
        return result
