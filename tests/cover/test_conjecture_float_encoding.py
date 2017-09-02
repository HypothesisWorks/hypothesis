# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

import sys
from random import Random

import pytest

import hypothesis.internal.conjecture.floats as flt
from hypothesis import strategies as st
from hypothesis import given, assume, example
from hypothesis.internal.compat import ceil, floor, hbytes, int_to_bytes, \
    int_from_bytes
from hypothesis.internal.floats import float_to_int
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.conjecture.minimizer import minimize

EXPONENTS = list(range(0, flt.MAX_EXPONENT + 1))
assert len(EXPONENTS) == 2 ** 11


def assert_reordered_exponents(res):
    res = list(res)
    assert len(res) == len(EXPONENTS)
    for x in res:
        assert res.count(x) == 1
        assert 0 <= x <= flt.MAX_EXPONENT


def test_encode_permutes_elements():
    assert_reordered_exponents(map(flt.encode_exponent, EXPONENTS))


def test_decode_permutes_elements():
    assert_reordered_exponents(map(flt.decode_exponent, EXPONENTS))


def test_decode_encode():
    for e in EXPONENTS:
        assert flt.decode_exponent(flt.encode_exponent(e)) == e


def test_encode_decode():
    for e in EXPONENTS:
        assert flt.decode_exponent(flt.encode_exponent(e)) == e


@given(st.data())
def test_double_reverse_bounded(data):
    n = data.draw(st.integers(1, 64))
    i = data.draw(st.integers(0, 2 ** n - 1))
    j = flt.reverse_bits(i, n)
    assert flt.reverse_bits(j, n) == i


@given(st.integers(0, 2 ** 64 - 1))
def test_double_reverse(i):
    j = flt.reverse64(i)
    assert flt.reverse64(j) == i


@example(1.25)
@example(1.0)
@given(st.floats())
def test_draw_write_round_trip(f):
    d = ConjectureData.for_buffer(hbytes(10))
    flt.write_float(d, f)
    d2 = ConjectureData.for_buffer(d.buffer)
    g = flt.draw_float(d2)

    if f == f:
        assert f == g

    assert float_to_int(f) == float_to_int(g)

    d3 = ConjectureData.for_buffer(d2.buffer)
    flt.draw_float(d3)
    assert d3.buffer == d2.buffer


@example(0.0)
@example(2.5)
@example(8.000000000000007)
@example(3.0)
@example(2.0)
@example(1.9999999999999998)
@example(1.0)
@given(st.floats(min_value=0.0))
def test_floats_round_trip(f):
    i = flt.float_to_lex(f)
    g = flt.lex_to_float(i)

    assert float_to_int(f) == float_to_int(g)


finite_floats = st.floats(allow_infinity=False, allow_nan=False, min_value=0.0)


@example(1.5)
@given(finite_floats)
def test_floats_order_worse_than_their_integral_part(f):
    assume(f != int(f))
    assume(int(f) != 0)
    i = flt.float_to_lex(f)
    if f < 0:
        g = ceil(f)
    else:
        g = floor(f)

    assert flt.float_to_lex(float(g)) < i


integral_floats = finite_floats.map(lambda x: float(int(x)))


@given(integral_floats, integral_floats)
def test_integral_floats_order_as_integers(x, y):
    assume(x != y)
    x, y = sorted((x, y))
    assume(y < 0 or x > 0)
    if y < 0:
        assert flt.float_to_lex(y) < flt.float_to_lex(x)
    else:
        assert flt.float_to_lex(x) < flt.float_to_lex(y)


@given(st.floats(0, 1))
def test_fractional_floats_are_worse_than_one(f):
    assume(0 < f < 1)
    assert flt.float_to_lex(f) > flt.float_to_lex(1)


def test_reverse_bits_table_reverses_bits():
    def bits(x):
        result = []
        for _ in range(8):
            result.append(x & 1)
            x >>= 1
        result.reverse()
        return result

    for i, b in enumerate(flt.REVERSE_BITS_TABLE):
        assert bits(i) == list(reversed(bits(b)))


def minimal_from(start, condition):
    buf = int_to_bytes(flt.float_to_lex(start), 8)

    def parse_buf(b): return flt.lex_to_float(int_from_bytes(b))
    shrunk = minimize(
        buf, lambda b: condition(parse_buf(b)),
        full=True, random=Random(0)
    )
    return parse_buf(shrunk)


INTERESTING_FLOATS = [
    0.0, 1.0, 2.0, sys.float_info.max, float('inf'), float('nan')
]


@pytest.mark.parametrize(('start', 'end'), [
    (a, b)
    for a in INTERESTING_FLOATS
    for b in INTERESTING_FLOATS
    if flt.float_to_lex(a) > flt.float_to_lex(b)
])
def test_can_shrink_downwards(start, end):
    assert minimal_from(start, lambda x: not (x < end)) == end


@pytest.mark.parametrize(
    'f', [1, 2, 4, 8, 10, 16, 32, 64, 100, 128, 256, 500, 512, 1000, 1024]
)
@pytest.mark.parametrize(
    'mul', [1.1, 1.5, 9.99, 10]
)
def test_shrinks_downwards_to_integers(f, mul):
    g = minimal_from(f * mul, lambda x: x >= f)
    assert g == f
