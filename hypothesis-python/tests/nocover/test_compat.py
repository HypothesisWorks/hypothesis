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

from hypothesis import given, strategies as st
from hypothesis.internal.compat import (
    ceil,
    floor,
    int_from_bytes,
    int_to_bytes,
    qualname,
)


class Foo:
    def bar(self):
        pass


def test_qualname():
    assert qualname(Foo.bar) == "Foo.bar"
    assert qualname(Foo().bar) == "Foo.bar"
    assert qualname(qualname) == "qualname"


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


@given(st.fractions())
def test_ceil(x):
    """The compat ceil function always has the Python 3 semantics.

    Under Python 2, math.ceil returns a float, which cannot represent large
    integers - for example, `float(2**53) == float(2**53 + 1)` - and this
    is obviously incorrect for unlimited-precision integer operations.
    """
    assert isinstance(ceil(x), int)
    assert x <= ceil(x) < x + 1


@given(st.fractions())
def test_floor(x):
    assert isinstance(floor(x), int)
    assert x - 1 < floor(x) <= x
