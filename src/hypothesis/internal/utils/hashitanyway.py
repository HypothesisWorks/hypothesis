# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, unicode_literals

from hypothesis.types import RandomWithSeed
from hypothesis.internal.compat import text_type, binary_type
from hypothesis.internal.extmethod import ExtMethod
from hypothesis.internal.utils.fixers import actually_equal

hash_everything = ExtMethod()


@hash_everything.extend(int)
@hash_everything.extend(float)
@hash_everything.extend(complex)
@hash_everything.extend(binary_type)
@hash_everything.extend(text_type)
@hash_everything.extend(bool)
@hash_everything.extend(RandomWithSeed)
def normal_hash(x):
    return hash(x)


@hash_everything.extend(dict)
def dict_hash(x):
    base = hash(type(x).__name__)
    for t in x.items():
        base ^= hash_everything(t)
    return base


@hash_everything.extend(type)
def type_hash(x):
    return hash(x.__name__)


@hash_everything.extend(object)
def generic_hash(x):
    h = hash(type(x).__name__)
    try:
        h ^= hash(len(x))
    except (TypeError, AttributeError):
        pass
    try:
        iter(x)
    except (TypeError, AttributeError):
        return h

    for y in x:
        h ^= hash_everything(y)
    return h


class HashItAnyway(object):

    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.h = hash_everything(wrapped)

    def __eq__(self, other):
        return (isinstance(other, HashItAnyway) and
                self.h == other.h and
                actually_equal(self.wrapped, other.wrapped))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return self.h

    def __repr__(self):
        return 'HashItAnyway(%s)' % repr(self.wrapped)
