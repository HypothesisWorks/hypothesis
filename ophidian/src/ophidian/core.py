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
                p = Python(**json.loads(blob))
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
            self.cache.put(p.path, json.dumps(attr.asdict(p)))
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
            value = json.loads(self.cache.get(key))
            return Python(**value)
        except KeyError:
            pass

        if not kwargs:
            result = next(self.pythons())
        else:
            def predicate(p):
                return all(
                    getattr(p, k) == v
                    for k, v in kwargs()
                )
            result = self.find_python(predicate)
        if result is None:
            raise ValueError('No such Python')
        self.cache.put(key, json.dumps(attr.asdict(result)))
        return result

    def find_python(self, predicate):
        for p in self.pythons():
            if predicate(p):
                return p
