# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import math

from hypothesis import given, strategies as st
from hypothesis.internal.compat import ceil, floor, int_from_bytes, int_to_bytes


@given(st.binary())
def test_convert_back(bs):
    bs = bytearray(bs)
    assert int_to_bytes(int_from_bytes(bs), len(bs)) == bs


bytes8 = st.builds(bytearray, st.binary(min_size=8, max_size=8))


@given(bytes8, bytes8)
def test_to_int_in_big_endian_order(x, y):
    x, y = sorted((x, y))
    assert 0 <= int_from_bytes(x) <= int_from_bytes(y)


ints8 = st.integers(min_value=0, max_value=2**63 - 1)


@given(ints8, ints8)
def test_to_bytes_in_big_endian_order(x, y):
    x, y = sorted((x, y))
    assert int_to_bytes(x, 8) <= int_to_bytes(y, 8)


@given(st.fractions())
def test_ceil(x):
    assert isinstance(ceil(x), int)
    assert x <= ceil(x) < x + 1
    assert ceil(x) == math.ceil(x)


@given(st.fractions())
def test_floor(x):
    assert isinstance(floor(x), int)
    assert x - 1 < floor(x) <= x
    assert floor(x) == math.floor(x)
