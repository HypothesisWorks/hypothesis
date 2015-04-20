# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from hypothesis.utils.show import show
from hypothesis.searchstrategy.strategies import BadData, strategy
from hypothesis.database.formats import JSONFormat
from hypothesis.database.backend import SQLiteBackend


class Storage(object):

    """Handles saving and loading examples matching a particular specifier."""

    def __repr__(self):
        return 'Storage(%s)' % (self.specifier,)

    def __init__(
        self, backend, specifier, strategy, format,
        database
    ):
        self.database = database
        self.backend = backend
        self.specifier = specifier
        self.format = format
        self.strategy = strategy
        self.key = show(specifier)

    def save(self, value):
        converted = self.strategy.to_basic(value)
        serialized = self.format.serialize_basic(converted)
        self.backend.save(self.key, serialized)

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

    Maps specifiers to storage for them.

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

    def storage_for(self, specifier, search_strategy=None):
        """Get a storage object corresponding to this specifier."""
        return Storage(
            specifier=specifier,
            database=self,
            backend=self.backend,
            format=self.format,
            strategy=search_strategy or strategy(specifier),
        )

    def close(self):
        self.backend.close()
