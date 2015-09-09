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

from hypothesis.specifiers import IntegerRange
from hypothesis.internal.compat import integer_types
from hypothesis.utils.extmethod import ExtMethod

matches_type = ExtMethod()


@matches_type.extend(type)
def type_matches(typ, value):
    return isinstance(value, typ)


@matches_type.extend(tuple)
def tuple_matches(tup, value):
    if not isinstance(value, type(tup)):
        return False
    if len(tup) != len(value):
        return False
    return all(
        matches_type(t, v) for t, v in zip(tup, value)
    )


@matches_type.extend(dict)
def dict_matches(d, value):
    if not isinstance(value, type(d)):
        return False
    if set(d) != set(value):
        return False
    return all(
        matches_type(v, value[k]) for k, v in d.items()
    )


@matches_type.extend(list)
def list_matches(ls, value):
    if not isinstance(value, type(ls)):
        return False
    if not ls and value:
        return False
    return all(
        any(matches_type(t, v) for t in ls)
        for v in value
    )


@matches_type.extend(IntegerRange)
def int_range_matches(r, value):
    return isinstance(value, integer_types) and (
        r.start <= value <= r.end
    )
