# coding=utf-8

from __future__ import division, print_function, absolute_import


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

class ClassMap(object):

    def __init__(self):
        self.data = {}

    def all_mappings(self, key):
        for c in type.mro(key):
            try:
                yield self.data[c]
            except KeyError:
                pass

    def __getitem__(self, key):
        try:
            return self.data[key]
        except KeyError:
            for m in self.all_mappings(key):
                return m
        raise KeyError(key)

    def __setitem__(self, key, value):
        self.data[key] = value
