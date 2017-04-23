# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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
import hashlib

import six

from ophidian.utils import randhex


class Storage(object):
    pass


class DictStorage(Storage):
    def __init__(self):
        self.__data = {}

    def put(self, key, value):
        self.__data[key] = value

    def get(self, key):
        return self.__data[key]

    def delete(self, key):
        try:
            del self.__data[key]
        except KeyError:
            pass

    def values(self):
        return self.__data.values()


def convert_to_binary(s):
    assert isinstance(s, (six.text_type, six.binary_type))
    if isinstance(s, six.text_type):
        s = s.encode('utf-8')
    return s


class DirStorage(Storage):
    def __init__(self, path):
        self.__path = path

    def put(self, key, value):
        # FIXME: This is not atomic on Windows and needs more careful handling.
        # Fortunately, ophidian isn't supporting Windows for its first pass
        # anyway!
        keyfile = self.__keyfile(key)
        try:
            os.unlink(keyfile)
        except OSError:
            pass
        value = convert_to_binary(value)
        tmpfile = self.__tmpfile()
        with open(tmpfile, 'wb') as o:
            o.write(value)
        try:
            os.rename(tmpfile, keyfile)
        except FileExistsError:
            os.unlink(tmpfile)

    def get(self, key):
        try:
            with open(self.__keyfile(key), 'rb') as i:
                return i.read()
        except IOError:
            raise KeyError(key)

    def delete(self, key):
        try:
            os.unlink(self.__keyfile(key))
        except OSError:
            pass

    def values(self):
        for c in os.listdir(self.__path):
            if not c.startswith('tmp-'):
                with open(os.path.join(self.__path, c), 'rb') as i:
                    result = i.read()
                yield result

    def __keyfile(self, key):
        return os.path.join(
            self.__path,
            hashlib.sha256(convert_to_binary(key)).hexdigest(),
        )

    def __tmpfile(self):
        return os.path.join(
            self.__path, 'tmp-%s' % (randhex(16),)
        )
