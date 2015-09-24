# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

import sqlite3
import threading
from abc import abstractmethod
from contextlib import contextmanager

from hypothesis.internal.compat import text_type


class Backend(object):

    """Interface class for storage systems.

    Simple text key -> value mapping. values are of the type returned by
    data_type() but keys are always unicode text (str in python 3, unicode in
    python 2).

    Every (key, value) pair appears at most once. Saving a duplicate will just
    silently do nothing.

    """

    @abstractmethod  # pragma: no cover
    def data_type(self):
        """Returns the type of data that is suitable for values in this DB."""

    @abstractmethod  # pragma: no cover
    def save(self, key, value):
        """Save a single value matching this key."""

    def delete(self, key, value):
        """Remove this value from this key.

        This method is optional but should fail silently if not
        supported. Note that if you do not support it you may see
        performance degradation over time as a number of values have to
        be ignored on each run

        """

    @abstractmethod  # pragma: no cover
    def fetch(self, key):
        """yield the values matching this key."""

    @abstractmethod  # pragma: no cover
    def close(self):
        """Close database connection whenever such is used."""


class SQLiteBackend(Backend):

    def __init__(self, path=u':memory:'):
        self.path = path
        self.db_created = False
        self.current_connection = threading.local()

    def connection(self):
        if not hasattr(self.current_connection, 'connection'):
            self.current_connection.connection = sqlite3.connect(self.path)
        return self.current_connection.connection

    def close(self):
        if hasattr(self.current_connection, 'connection'):
            try:
                self.connection().close()
            finally:
                del self.current_connection.connection

    def __repr__(self):
        return u'%s(%s)' % (self.__class__.__name__, self.path)

    def data_type(self):
        return text_type

    @contextmanager
    def cursor(self):
        conn = self.connection()
        cursor = conn.cursor()
        try:
            try:
                yield cursor
            finally:
                cursor.close()
        except:
            conn.rollback()
            raise
        else:
            conn.commit()

    def save(self, key, value):
        self.create_db_if_needed()
        with self.cursor() as cursor:
            try:
                cursor.execute("""
                    insert into hypothesis_data_mapping(key, value)
                    values(?, ?)
                """, (key, value))
            except sqlite3.IntegrityError:
                pass

    def delete(self, key, value):
        self.create_db_if_needed()
        with self.cursor() as cursor:
            cursor.execute("""
                delete from hypothesis_data_mapping
                where key = ? and value = ?
            """, (key, value))

    def fetch(self, key):
        self.create_db_if_needed()
        with self.cursor() as cursor:
            cursor.execute("""
                select value from hypothesis_data_mapping
                where key = ?
            """, (key,))
            return [value for (value,) in cursor]

    def keys(self):
        """Iterate over all keys in the database."""
        self.create_db_if_needed()
        with self.cursor() as cursor:
            cursor.execute("""
                select distinct key from hypothesis_data_mapping
            """)
            for (key,) in cursor:
                yield key

    def create_db_if_needed(self):
        if self.db_created:
            return
        with self.cursor() as cursor:
            cursor.execute("""
                create table if not exists hypothesis_data_mapping(
                    key text,
                    value text,
                    unique(key, value)
                )
            """)
        self.db_created = True
