# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import os
import re
import base64
import hashlib
import sqlite3
import binascii
import threading
from contextlib import contextmanager

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

    Simple binary key -> value mapping.

    Keys and values are binary data.

    Every (key, value) pair appears at most once. Saving a duplicate will just
    silently do nothing.

    """

    def delete(self, key, value):
        """Remove this value from this key.

        This method is optional but should fail silently if not
        supported. Note that if you do not support it you may see
        performance degradation over time as a number of values have to
        be ignored on each run

        """
        raise NotImplementedError('%s.delete' % (type(self).__name__))

    def fetch(self, key):
        """yield the values matching this key."""
        raise NotImplementedError('%s.fetch' % (type(self).__name__))

    def save(self, key, value):
        """save this value under this key."""
        raise NotImplementedError('%s.save' % (type(self).__name__))

    def keys(self):
        raise NotImplementedError('%s.keys' % (type(self).__name__))

    def close(self):
        """Close database connection whenever such is used."""
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
        self.data.setdefault(key, set()).add(value)

    def delete(self, key, value):
        self.data.get(key, set()).discard(value)

    def keys(self):
        for k, v in self.data.items():
            if v:
                yield k

    def close(self):
        pass


class SQLiteExampleDatabase(ExampleDatabase):

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
                """, (base64.b64encode(key), base64.b64encode(value)))
            except sqlite3.IntegrityError:
                pass

    def delete(self, key, value):
        self.create_db_if_needed()
        with self.cursor() as cursor:
            cursor.execute("""
                delete from hypothesis_data_mapping
                where key = ? and value = ?
            """, (base64.b64encode(key), base64.b64encode(value)))

    def fetch(self, key):
        self.create_db_if_needed()
        with self.cursor() as cursor:
            cursor.execute("""
                select value from hypothesis_data_mapping
                where key = ?
            """, (base64.b64encode(key),))
            for (value,) in cursor:
                try:
                    yield base64.b64decode(value)
                except binascii.Error:
                    pass

    def keys(self):
        """Iterate over all keys in the database."""
        self.create_db_if_needed()
        with self.cursor() as cursor:
            cursor.execute("""
                select distinct key from hypothesis_data_mapping
            """)
            for (key,) in cursor:
                try:
                    yield base64.b64decode(key)
                except binascii.Error:
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
    return hashlib.sha1(key).hexdigest()[:16]


class DirectoryBasedExampleDatabase(ExampleDatabase):

    def __init__(self, path):
        self.path = path
        self.keypaths = {}

    def __repr__(self):
        return 'DirectoryBasedExampleDatabase(%r)' % (self.path,)

    def create_db_if_needed(self):
        mkdirp(self.path)

    def close(self):
        pass

    def keys(self):
        self.create_db_if_needed()
        for d in os.listdir(self.path):
            files = os.listdir(os.path.join(self.path, d))
            if len(files) > 1 and 'name' in files:
                namefile = os.path.join(self.path, d, 'name')
                with open(namefile, 'rb') as i:
                    result = i.read()
                if _hash(result) == d:
                    yield result

    def _key_path(self, key):
        try:
            return self.keypaths[key]
        except KeyError:
            pass
        directory = os.path.join(self.path, _hash(key))
        mkdirp(directory)
        namefile = os.path.join(directory, 'name')
        if os.path.exists(namefile):
            with open(namefile, 'rb') as r:
                ex = r.read()
            if ex != key:
                os.unlink(namefile)
        if not os.path.exists(namefile):
            tmpname = os.path.join(
                directory, str(binascii.hexlify(os.urandom(16))))
            with open(tmpname, 'wb') as w:
                w.write(key)
            try:
                os.rename(tmpname, namefile)
            except OSError:  # pragma: no cover
                os.unlink(tmpname)
        assert os.path.exists(namefile)
        self.keypaths[key] = directory
        return directory

    def _value_path(self, key, value):
        return os.path.join(
            self._key_path(key),
            hashlib.sha1(value).hexdigest()[:16]
        )

    def fetch(self, key):
        kp = self._key_path(key)
        for path in os.listdir(kp):
            if path != 'name':
                with open(os.path.join(kp, path), 'rb') as i:
                    yield i.read()

    def save(self, key, value):
        with open(self._value_path(key, value), 'wb') as o:
            o.write(value)

    def delete(self, key, value):
        try:
            os.unlink(self._value_path(key, value))
        except OSError:
            pass
