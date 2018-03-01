# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import os
import re
import binascii
import threading
from hashlib import sha1
from contextlib import contextmanager

from hypothesis._settings import note_deprecation
from hypothesis.internal.compat import FileNotFoundError, hbytes, \
    b64decode, b64encode

sqlite3 = None
SQLITE_PATH = re.compile(r"\.\(db|sqlite|sqlite3\)$")


def _db_for_path(path=None):
    if path in (None, ':memory:'):
        return InMemoryExampleDatabase()
    path = str(path)
    if os.path.isdir(path):
        return DirectoryBasedExampleDatabase(path)
    if os.path.exists(path):
        return SQLiteExampleDatabase(path)
    if SQLITE_PATH.search(path):
        return SQLiteExampleDatabase(path)
    else:
        return DirectoryBasedExampleDatabase(path)


class EDMeta(type):

    def __call__(self, *args, **kwargs):
        if self is ExampleDatabase:
            return _db_for_path(*args, **kwargs)
        return super(EDMeta, self).__call__(*args, **kwargs)


class ExampleDatabase(EDMeta('ExampleDatabase', (object,), {})):
    """Interface class for storage systems.

    A key -> multiple distinct values mapping.

    Keys and values are binary data.
    """

    def save(self, key, value):
        """Save ``value`` under ``key``.

        If this value is already present for this key, silently do
        nothing
        """
        raise NotImplementedError('%s.save' % (type(self).__name__))

    def delete(self, key, value):
        """Remove this value from this key.

        If this value is not present, silently do nothing.
        """
        raise NotImplementedError('%s.delete' % (type(self).__name__))

    def move(self, src, dest, value):
        """Move value from key src to key dest. Equivalent to delete(src,
        value) followed by save(src, value) but may have a more efficient
        implementation.

        Note that value will be inserted at dest regardless of whether
        it is currently present at src.
        """
        if src == dest:
            self.save(src, value)
            return
        self.delete(src, value)
        self.save(dest, value)

    def fetch(self, key):
        """Return all values matching this key."""
        raise NotImplementedError('%s.fetch' % (type(self).__name__))

    def close(self):
        """Clear up any resources associated with this database."""
        raise NotImplementedError('%s.close' % (type(self).__name__))


class InMemoryExampleDatabase(ExampleDatabase):

    def __init__(self):
        self.data = {}

    def __repr__(self):
        return 'InMemoryExampleDatabase(%r)' % (self.data,)

    def fetch(self, key):
        for v in self.data.get(key, ()):
            yield v

    def save(self, key, value):
        self.data.setdefault(key, set()).add(hbytes(value))

    def delete(self, key, value):
        self.data.get(key, set()).discard(hbytes(value))

    def close(self):
        pass


class SQLiteExampleDatabase(ExampleDatabase):

    def __init__(self, path=u':memory:'):
        self.path = path
        self.db_created = False
        self.current_connection = threading.local()
        global sqlite3
        import sqlite3

        if path == u':memory:':
            note_deprecation(
                'The SQLite database backend has been deprecated. '
                'Use InMemoryExampleDatabase or set database_file=":memory:" '
                'instead.'
            )
        else:
            note_deprecation(
                'The SQLite database backend has been deprecated. '
                'Set database_file to some path name not ending in .db, '
                '.sqlite or .sqlite3 to get the new directory based database '
                'backend instead.'
            )

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

    @contextmanager
    def cursor(self):
        conn = self.connection()
        cursor = conn.cursor()
        try:
            try:
                yield cursor
            finally:
                cursor.close()
        except BaseException:
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
                """, (b64encode(key), b64encode(value)))
            except sqlite3.IntegrityError:
                pass

    def delete(self, key, value):
        self.create_db_if_needed()
        with self.cursor() as cursor:
            cursor.execute("""
                delete from hypothesis_data_mapping
                where key = ? and value = ?
            """, (b64encode(key), b64encode(value)))

    def fetch(self, key):
        self.create_db_if_needed()
        with self.cursor() as cursor:
            cursor.execute("""
                select value from hypothesis_data_mapping
                where key = ?
            """, (b64encode(key),))
            for (value,) in cursor:
                try:
                    yield b64decode(value)
                except (binascii.Error, TypeError):
                    pass

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


def mkdirp(path):
    try:
        os.makedirs(path)
    except OSError:
        pass
    return path


def _hash(key):
    return sha1(key).hexdigest()[:16]


class DirectoryBasedExampleDatabase(ExampleDatabase):

    def __init__(self, path):
        self.path = path
        self.keypaths = {}

    def __repr__(self):
        return 'DirectoryBasedExampleDatabase(%r)' % (self.path,)

    def close(self):
        pass

    def _key_path(self, key):
        try:
            return self.keypaths[key]
        except KeyError:
            pass
        directory = os.path.join(self.path, _hash(key))
        mkdirp(directory)
        self.keypaths[key] = directory
        return directory

    def _value_path(self, key, value):
        return os.path.join(
            self._key_path(key),
            sha1(value).hexdigest()[:16]
        )

    def fetch(self, key):
        kp = self._key_path(key)
        for path in os.listdir(kp):
            try:
                with open(os.path.join(kp, path), 'rb') as i:
                    yield hbytes(i.read())
            except FileNotFoundError:
                pass

    def save(self, key, value):
        path = self._value_path(key, value)
        if not os.path.exists(path):
            suffix = binascii.hexlify(os.urandom(16))
            if not isinstance(suffix, str):  # pragma: no branch
                # On Python 3, binascii.hexlify returns bytes
                suffix = suffix.decode('ascii')
            tmpname = path + '.' + suffix
            with open(tmpname, 'wb') as o:
                o.write(value)
            try:
                os.rename(tmpname, path)
            except OSError:  # pragma: no cover
                os.unlink(tmpname)
            assert not os.path.exists(tmpname)

    def move(self, src, dest, value):
        if src == dest:
            self.save(src, value)
            return
        try:
            os.rename(
                self._value_path(src, value), self._value_path(dest, value))
        except OSError:
            self.delete(src, value)
            self.save(dest, value)

    def delete(self, key, value):
        try:
            os.unlink(self._value_path(key, value))
        except OSError:
            pass
