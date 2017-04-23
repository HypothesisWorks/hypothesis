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

import attr
from ophidian.finder import find_pythons, python_for_exe
from ophidian.storage import DictStorage


@attr.s
class Ophidian(object):
    cache = attr.ib(default=attr.Factory(DictStorage))
    installer = attr.ib(default=None)
    paths = attr.ib(default=None)

    __python_iterator = None
    __found_pythons = None
    __seen_paths = set()

    def pythons(self):
        if self.__found_pythons is None:
            self.__found_pythons = []
            self.__seen_paths = set()
            self.__python_iterator = find_pythons(
                skip_path=lambda p: p in self.__seen_paths)

        for p in self.__found_pythons:
            yield p

        def note(p):
            self.__found_pythons.append(p)
            self.__seen_paths.add(p.path)
            return p

        for p in self.cache.values():
            if p.stale:
                if os.path.exists(p.path):
                    p = python_for_exe(p.path)
                else:
                    continue
            yield note(p)

        for p in self.__python_iterator:
            yield note(p)

    def find_python(self, predicate):
        for p in self.pythons():
            if predicate(p):
                return p
