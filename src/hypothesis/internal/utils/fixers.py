# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""This is a module for functions I consider to be designed to work around
Python doing entirely the wrong thing.

You can imagine how grumpy I was when I wrote it.

"""

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import math
import unittest

from hypothesis.internal.compat import text_type, binary_type, \
    integer_types
from hypothesis.internal.extmethod import ExtMethod
from hypothesis.internal.utils.reflection import unbind_method


class Equality(ExtMethod):

    def __call__(self, x, y, fuzzy=False):
        if x is y:
            return True
        if type(x) != type(y):
            return False
        return super(Equality, self).__call__(x, y, fuzzy)


equal = Equality()


primitives = [
    int, float, bool, type, text_type, binary_type
] + list(integer_types)


@equal.extend(object)
def generic_equal(x, y, fuzzy):
    try:
        if len(x) != len(y):
            return False
    except (TypeError, AttributeError):
        pass
    try:
        iter(x)
        iter(y)
    except TypeError:
        return x == y
    return actually_equal(
        tuple(x), tuple(y), fuzzy
    )


@equal.extend(int)
@equal.extend(bool)
@equal.extend(type)
@equal.extend(text_type)
@equal.extend(binary_type)
def primitive_equal(x, y, fuzzy):
    return x == y


@equal.extend(float)
def float_equal(x, y, fuzzy=False):
    if math.isnan(x) and math.isnan(y):
        return True
    if x == y:
        return True
    return fuzzy and (repr(x) == repr(y))


@equal.extend(complex)
def complex_equal(x, y, fuzzy=False):
    return (
        float_equal(x.real, y.real, fuzzy) and
        float_equal(x.imag, y.imag, fuzzy)
    )


@equal.extend(tuple)
@equal.extend(list)
def sequence_equal(x, y, fuzzy=False):
    if len(x) != len(y):
        return False
    for u, v in zip(x, y):
        if not actually_equal(u, v, fuzzy):
            return False
    return True


@equal.extend(set)
@equal.extend(frozenset)
def set_equal(x, y, fuzzy=False):
    if len(x) != len(y):
        return False
    for u in x:
        if not actually_in(u, y):
            return False
    return True


@equal.extend(dict)
def dict_equal(x, y, fuzzy=False):
    if len(x) != len(y):
        return False
    for k, v in x.items():
        if k not in y:
            return False
        if not actually_equal(x[k], y[k], fuzzy):
            return False
    return True


def actually_equal(x, y, fuzzy=False):
    return equal(x, y, fuzzy)


def actually_in(x, ys, fuzzy=False):
    return any(actually_equal(x, y, fuzzy) for y in ys)


def real_index(value, y, fuzzy=False):
    i = 0
    while i < len(value):
        if actually_equal(value[i], y, fuzzy):
            return i
        i += 1
    raise ValueError('%r is not in list %r' % (y, value))


def is_nasty_float(x):
    return math.isnan(x) or math.isinf(x)


class IdKey(object):

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return (type(other) == IdKey) and (self.value is other.value)

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __hash__(self):
        return hash(id(self.value))


class IdentitySet(object):

    def __init__(self):
        self.data = {}

    def __contains__(self, value):
        key = IdKey(value)
        return self.data.get(key, 0) > 0

    def add(self, value):
        key = IdKey(value)
        self.data[key] = self.data.get(key, 0) + 1

    def remove(self, value):
        key = IdKey(value)
        self.data[key] = self.data.get(key, 0) - 1


class NiceString(ExtMethod):

    def __call__(self, value, seen=None):
        if seen is None:
            seen = IdentitySet()
        if value in seen:
            return '(...)'
        seen.add(value)
        result = super(NiceString, self).__call__(value, seen)
        seen.remove(value)
        return result


nice_string = NiceString()


@nice_string.extend(bool)
def repr_string(value, seen):
    return repr(value)


@nice_string.extend(object)
def generic_string(value, seen):
    if hasattr(value, '__name__'):
        return value.__name__
    try:
        d = value.__dict__
    except AttributeError:
        if type(value) == object:
            return 'object()'
        else:
            return repr(value)
    if (
        unbind_method(type(value).__repr__) != unbind_method(object.__repr__)
    ):
        return repr(value)
    else:
        return '%s(%s)' % (
            value.__class__.__name__,
            ', '.join(
                '%s=%s' % (
                    k2, nice_string(v2, seen)
                ) for k2, v2 in d.items()
            )
        )


@nice_string.extend(text_type)
def text_string(value, seen):
    result = repr(value)
    if result[0] == 'u':  # pragma: no branch
        return result[1:]  # pragma: no cover
    else:
        return result  # pragma: no cover


@nice_string.extend(binary_type)
def binary_string(value, seen):
    result = repr(value)
    if result[0] != 'b':  # pragma: no branch
        return 'b' + result  # pragma: no cover
    else:
        return result  # pragma: no cover


@nice_string.extend(type)
def type_string(value, seen):
    return value.__name__


@nice_string.extend(float)
def float_string(value, seen):
    if is_nasty_float(value):
        return 'float(%r)' % (str(value),)
    else:
        return repr(value)


@nice_string.extend(complex)
def complex_string(x, seen):
    if is_nasty_float(x.real) or is_nasty_float(x.imag):
        r = repr(x)
        if r[0] == '(' and r[-1] == ')':
            r = r[1:-1]
        return 'complex(%r)' % (r,)
    else:
        return repr(x)


@nice_string.extend(list)
def list_string(value, seen):
    return '[%s]' % (', '.join(
        nice_string(c, seen) for c in value
    ))


@nice_string.extend(set)
def set_string(value, seen):
    if value:
        return '{%s}' % (', '.join(sorted(
            nice_string(c, seen) for c in value
        )))
    else:
        return repr(value)


@nice_string.extend(frozenset)
def frozenset_string(value, seen):
    if value:
        return 'frozenset({%s})' % (', '.join(sorted(
            nice_string(c, seen) for c in value
        )))
    else:
        return repr(value)


@nice_string.extend(tuple)
def tuple_string(value, seen):
    if hasattr(value, '_fields'):
        return '%s(%s)' % (
            value.__class__.__name__,
            ', '.join(
                '%s=%s' % (f, nice_string(getattr(value, f), seen))
                for f in value._fields))
    else:
        core = ', '.join(
            nice_string(c, seen) for c in value
        )
        if len(value) == 1:
            core += ','
        return '(%s)' % (core,)


@nice_string.extend(dict)
def dict_string(value, seen):
    return '{' + ', '.join(sorted([
        nice_string(k1, seen) + ': ' + nice_string(v1, seen)
        for k1, v1 in value.items()
    ])) + '}'


@nice_string.extend(unittest.TestCase)
def test_string(value, seen):
    return '%s(methodName=%r)' % (
        type(value).__name__,
        value._testMethodName,
    )


def int_string(value, seen):
    s = repr(value)
    if s[-1] == 'L':  # pragma: no branch
        s = s[:-1]  # pragma: no cover
    return s

for t in integer_types:
    nice_string.extend(t)(int_string)
