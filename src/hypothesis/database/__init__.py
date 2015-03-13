# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from hypothesis.internal.fixers import nice_string
from hypothesis.internal.hashitanyway import HashItAnyway
from hypothesis.internal.tracker import Tracker
from hypothesis.searchstrategy import BadData, strategy
from hypothesis.database.formats import JSONFormat
from hypothesis.database.backend import SQLiteBackend


class Storage(object):

    """Handles saving and loading examples matching a particular descriptor."""

    def __repr__(self):
        return 'Storage(%s)' % (self.descriptor,)

    def __init__(
        self, backend, descriptor, strategy, format,
        database
    ):
        self.database = database
        self.backend = backend
        self.descriptor = descriptor
        self.format = format
        self.strategy = strategy
        self.key = nice_string(descriptor)

    def save(self, value):
        tracker = Tracker()

        def do_save(d, v):
            if tracker.track((d, v)) > 1:
                return
            s = self.database.storage_for(d)
            converted = s.strategy.to_basic(v)
            serialized = s.format.serialize_basic(converted)
            s.backend.save(s.key, serialized)

            for d2, v2 in s.strategy.decompose(v):
                do_save(d2, v2)

        do_save(self.descriptor, value)

    def fetch(self):
        for data in self.backend.fetch(self.key):
            try:
                deserialized = self.strategy.from_basic(
                    self.format.deserialize_data(data))
            except BadData:
                self.backend.delete(self.key, data)
                continue

            yield deserialized


class ExampleDatabase(object):

    """Object encapsulating all the things you need to get storage.

    Maps descriptors to storage for them.

    """

    def __repr__(self):
        return 'ExampleDatabase(%r, %r)' % (
            self.backend, self.format
        )

    def __init__(
        self,
        backend=None,
        format=None,
    ):
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
            strategy=strategy(descriptor),
        )
        self.storage_cache[key] = result
        return result
