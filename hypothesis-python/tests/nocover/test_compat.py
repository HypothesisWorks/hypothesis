# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

import inspect
import warnings

import pytest

from hypothesis import given, strategies as st
from hypothesis.internal.compat import (
    FullArgSpec,
    ceil,
    floor,
    getfullargspec,
    hrange,
    int_from_bytes,
    int_to_bytes,
    integer_types,
    qualname,
)


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


class Foo:
    def bar(self):
        pass


def test_qualname():
    assert qualname(Foo.bar) == "Foo.bar"
    assert qualname(Foo().bar) == "Foo.bar"
    assert qualname(qualname) == "qualname"


def a(b, c, d):
    pass


def b(c, d, *ar):
    pass


def c(c, d, *ar, **k):
    pass


def d(a1, a2=1, a3=2, a4=None):
    pass


@pytest.mark.parametrize("f", [a, b, c, d])
def test_agrees_on_argspec(f):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        basic = inspect.getargspec(f)
    full = getfullargspec(f)
    assert basic.args == full.args
    assert basic.varargs == full.varargs
    assert basic.keywords == full.varkw
    assert basic.defaults == full.defaults


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


@pytest.mark.skipif(
    not hasattr(inspect, "getfullargspec"),
    reason="inspect.getfullargspec only exists under Python 3",
)
def test_inspection_compat():
    assert getfullargspec is inspect.getfullargspec


@pytest.mark.skipif(
    not hasattr(inspect, "FullArgSpec"),
    reason="inspect.FullArgSpec only exists under Python 3",
)
def test_inspection_result_compat():
    assert FullArgSpec is inspect.FullArgSpec


@given(st.fractions())
def test_ceil(x):
    """The compat ceil function always has the Python 3 semantics.

    Under Python 2, math.ceil returns a float, which cannot represent large
    integers - for example, `float(2**53) == float(2**53 + 1)` - and this
    is obviously incorrect for unlimited-precision integer operations.
    """
    assert isinstance(ceil(x), integer_types)
    assert x <= ceil(x) < x + 1


@given(st.fractions())
def test_floor(x):
    assert isinstance(floor(x), integer_types)
    assert x - 1 < floor(x) <= x
