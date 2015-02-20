# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from hypothesis.internal.compat import hrange
from hypothesis.internal.utils.fixers import actually_equal

collection_types = (set, frozenset, tuple, list)


def mutate_slightly(random, d):
    if isinstance(d, collection_types):
        bits = tuple(
            mutate_slightly(random, x)
            for x in d
        )
        try:
            hash(bits)
            valid_types = collection_types
        except TypeError:
            valid_types = (tuple, list)
        return random.choice(valid_types)(bits)

    if isinstance(d, dict):
        result = {}
        for k, v in d.items():
            result[k] = mutate_slightly(random, v)
        return result
    return d


def mutate_maliciously(random, d):
    for _ in hrange(10):
        d2 = mutate_slightly(random, d)
        if d == d2 and not actually_equal(d, d2):
            return d2
    return d2
