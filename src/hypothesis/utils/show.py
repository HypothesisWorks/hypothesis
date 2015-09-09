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

import math
import unittest

import hypothesis.internal.reflection as reflection
from hypothesis.utils.idkey import IdentitySet
from hypothesis.internal.compat import text_type, binary_type, \
    integer_types
from hypothesis.utils.extmethod import ExtMethod


class Show(ExtMethod):

    def __call__(self, value, seen=None):
        if seen is None:
            seen = IdentitySet()
        if value in seen:
            return u'(...)'
        seen.add(value)
        result = super(Show, self).__call__(value, seen)
        seen.remove(value)
        return result


show = Show()


@show.extend(bool)
def repr_string(value, seen):
    return repr(value)


@show.extend(object)
def generic_string(value, seen):
    if hasattr(value, u'__name__'):
        return value.__name__
    try:
        d = value.__dict__
    except AttributeError:
        if type(value) == object:
            return u'object()'
        else:
            return repr(value)
    if (
        reflection.unbind_method(type(value).__repr__) !=
        reflection.unbind_method(object.__repr__)
    ):
        return repr(value)
    else:
        return u'%s(%s)' % (
            value.__class__.__name__,
            u', '.join(
                u'%s=%s' % (
                    k2, show(v2, seen)
                ) for k2, v2 in d.items()
            )
        )


@show.extend(text_type)
def text_string(value, seen):
    result = repr(value)
    if result[0] == u'u':  # pragma: no branch
        return result[1:]  # pragma: no cover
    else:
        return result  # pragma: no cover


@show.extend(binary_type)
def binary_string(value, seen):
    result = repr(value)
    if result[0] != u'b':  # pragma: no branch
        return u'b' + result  # pragma: no cover
    else:
        return result  # pragma: no cover


@show.extend(type)
def type_string(value, seen):
    return value.__name__


def is_nasty_float(x):
    return math.isnan(x) or math.isinf(x)


@show.extend(float)
def float_string(value, seen):
    if is_nasty_float(value):
        return u'float(%r)' % (str(value),)
    else:
        return repr(value)


@show.extend(complex)
def complex_string(x, seen):
    if is_nasty_float(x.real) or is_nasty_float(x.imag):
        r = repr(x)
        if r[0] == u'(' and r[-1] == u')':
            r = r[1:-1]
        return u'complex(%r)' % (r,)
    else:
        return repr(x)


@show.extend(list)
def list_string(value, seen):
    return u'[%s]' % (u', '.join(
        show(c, seen) for c in value
    ))


@show.extend(set)
def set_string(value, seen):
    if value:
        return u'{%s}' % (u', '.join(sorted(
            show(c, seen) for c in value
        )))
    else:
        return repr(value)


@show.extend(frozenset)
def frozenset_string(value, seen):
    if value:
        return u'frozenset({%s})' % (u', '.join(sorted(
            show(c, seen) for c in value
        )))
    else:
        return repr(value)


@show.extend(tuple)
def tuple_string(value, seen):
    if hasattr(value, u'_fields'):
        return u'%s(%s)' % (
            value.__class__.__name__,
            u', '.join(
                u'%s=%s' % (f, show(getattr(value, f), seen))
                for f in value._fields))
    else:
        core = u', '.join(
            show(c, seen) for c in value
        )
        if len(value) == 1:
            core += u','
        return u'(%s)' % (core,)


@show.extend(dict)
def dict_string(value, seen):
    return u'{' + u', '.join(sorted([
        show(k1, seen) + u': ' + show(v1, seen)
        for k1, v1 in value.items()
    ])) + u'}'


@show.extend(unittest.TestCase)
def test_string(value, seen):
    return u'%s(methodName=%r)' % (
        type(value).__name__,
        value._testMethodName,
    )


def int_string(value, seen):
    s = repr(value)
    if s[-1] == u'L':  # pragma: no branch
        s = s[:-1]  # pragma: no cover
    return s

for t in integer_types:
    show.extend(t)(int_string)
