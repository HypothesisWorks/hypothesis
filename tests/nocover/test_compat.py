# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

import pytest

from hypothesis import strategies as st
from hypothesis import given
from hypothesis.internal.compat import hrange, qualname, int_to_bytes, \
    HAS_SIGNATURE, int_from_bytes, signature_argspec


def test_small_hrange():
    assert list(hrange(5)) == [0, 1, 2, 3, 4]
    assert list(hrange(3, 5)) == [3, 4]
    assert list(hrange(1, 10, 2)) == [1, 3, 5, 7, 9]


def test_large_hrange():
    n = 1 << 1024
    assert list(hrange(n, n + 5, 2)) == [n, n + 2, n + 4]
    assert list(hrange(n, n)) == []

    with pytest.raises(ValueError):
        hrange(n, n, 0)


class Foo():

    def bar(self):
        pass


def test_qualname():
    assert qualname(Foo.bar) == u'Foo.bar'
    assert qualname(Foo().bar) == u'Foo.bar'
    assert qualname(qualname) == u'qualname'

try:
    from inspect import getargspec
except ImportError:
    getargspec = None


def a(b, c, d):
    pass


def b(c, d, *ar):
    pass


def c(c, d, *ar, **k):
    pass


def d(a1, a2=1, a3=2, a4=None):
    pass

if getargspec is not None and HAS_SIGNATURE:
    @pytest.mark.parametrize('f', [
        a, b, c, d
    ])
    def test_agrees_on_argspec(f):
        real = getargspec(f)
        fake = signature_argspec(f)
        assert tuple(real) == tuple(fake)
        for f in real._fields:
            assert getattr(real, f) == getattr(fake, f)


@given(st.binary())
def test_convert_back(bs):
    bs = bytearray(bs)
    assert int_to_bytes(int_from_bytes(bs), len(bs)) == bs

bytes8 = st.builds(bytearray, st.binary(min_size=8, max_size=8))


@given(bytes8, bytes8)
def test_to_int_in_big_endian_order(x, y):
    x, y = sorted((x, y))
    assert 0 <= int_from_bytes(x) <= int_from_bytes(y)


ints8 = st.integers(min_value=0, max_value=2 ** 63 - 1)


@given(ints8, ints8)
def test_to_bytes_in_big_endian_order(x, y):
    x, y = sorted((x, y))
    assert int_to_bytes(x, 8) <= int_to_bytes(y, 8)
