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
import json

import attr
from ophidian.finder import Python, find_pythons, python_for_exe
from ophidian.storage import DictStorage

PYTHON_FIELDS = frozenset(t.name for t in attr.fields(Python))

FORMAT_VERSION = 1

FORMAT_FIELD = 'format-version'


def blob_to_python(blob):
    """Attempt to interpert blob as a valid Python object or return None
    otherwise."""
    try:
        values = json.loads(blob)
    except ValueError:
        return None
    version = values.pop(FORMAT_FIELD, None)
    if version != FORMAT_VERSION:
        return None
    if frozenset(values) != PYTHON_FIELDS:
        return None
    return Python(**values)


def python_to_blob(python):
    values = attr.asdict(python)
    values[FORMAT_FIELD] = FORMAT_VERSION
    return json.dumps(values).encode('utf-8')


class NoSuchPython(Exception):
    pass


@attr.s
class Ophidian(object):
    cache = attr.ib(default=attr.Factory(DictStorage))
    installer = attr.ib(default=None)
    paths = attr.ib(default=None)

    __python_iterator = None
    __found_pythons = None
    __seen_paths = set()
    __added_cache = False

    def pythons(self):
        if self.__found_pythons is None:
            self.__found_pythons = []
            self.__seen_paths = set()
            self.__python_iterator = find_pythons(
                skip_path=lambda p: p in self.__seen_paths)

        if not self.__added_cache:
            for blob in self.cache.values():
                p = blob_to_python(blob)
                if p is None:
                    continue
                if p.stale:
                    if os.path.exists(p.path):
                        p = python_for_exe(p.path)
                    else:
                        continue
                self.__found_pythons.append(p)
                self.__seen_paths.add(p.path)
            self.__added_cache = True

        def note(p):
            self.__found_pythons.append(p)
            self.__seen_paths.add(p.path)
            self.cache.put(p.path, python_to_blob(p))
            return p

        for p in self.__found_pythons:
            yield p

        for p in self.__python_iterator:
            yield note(p)

    def get_python(self, **kwargs):
        for k, v in list(kwargs.items()):
            if v is None:
                del kwargs[k]
        key = ','.join('%s-%r' % t for t in sorted(kwargs.items()))
        try:
            result = blob_to_python(self.cache.get(key))
            if result is not None and not result.stale:
                return result
        except KeyError:
            pass

        if not kwargs:
            result = next(self.pythons())
        else:
            def predicate(p):
                return all(
                    getattr(p, k) == v
                    for k, v in kwargs.items()
                )
            result = self.find_python(predicate)
        if result is None:
            if self.installer is not None:
                result = python_for_exe(self.installer.install(**kwargs))
                self.cache.put(result.path, python_to_blob(result))
            else:
                raise NoSuchPython('No such Python')
        self.cache.put(key, python_to_blob(result))
        return result

    def find_python(self, predicate):
        for p in self.pythons():
            if predicate(p):
                return p
