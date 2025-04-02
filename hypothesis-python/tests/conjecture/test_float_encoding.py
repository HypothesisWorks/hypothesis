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
import sys

import pytest

from hypothesis import HealthCheck, assume, example, given, settings, strategies as st
from hypothesis.internal.compat import ceil, extract_bits, floor
from hypothesis.internal.conjecture import floats as flt
from hypothesis.internal.conjecture.engine import ConjectureRunner
from hypothesis.internal.floats import SIGNALING_NAN, float_to_int

EXPONENTS = list(range(flt.MAX_EXPONENT + 1))
assert len(EXPONENTS) == 2**11


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
    i = data.draw(st.integers(0, 2**n - 1))
    j = flt.reverse_bits(i, n)
    assert flt.reverse_bits(j, n) == i


@given(st.integers(0, 2**64 - 1))
def test_double_reverse(i):
    j = flt.reverse64(i)
    assert flt.reverse64(j) == i


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


@settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
@example(1, 0.5)
@given(st.integers(1, 2**53), st.floats(0, 1).filter(lambda x: x not in (0, 1)))
def test_floats_order_worse_than_their_integral_part(n, g):
    f = n + g
    assume(int(f) != f)
    assume(int(f) != 0)
    i = flt.float_to_lex(f)
    if f < 0:
        g = ceil(f)
    else:
        g = floor(f)

    assert flt.float_to_lex(float(g)) < i


integral_floats = st.floats(allow_infinity=False, allow_nan=False, min_value=0.0).map(
    lambda x: abs(float(int(x)))
)


@given(integral_floats, integral_floats)
def test_integral_floats_order_as_integers(x, y):
    assume(x != y)
    x, y = sorted((x, y))
    assert flt.float_to_lex(x) < flt.float_to_lex(y)


@given(st.floats(0, 1))
def test_fractional_floats_are_worse_than_one(f):
    assume(0 < f < 1)
    assert flt.float_to_lex(f) > flt.float_to_lex(1)


def test_reverse_bits_table_reverses_bits():
    for i, b in enumerate(flt.REVERSE_BITS_TABLE):
        assert extract_bits(i, width=8) == list(reversed(extract_bits(b, width=8)))


def test_reverse_bits_table_has_right_elements():
    assert sorted(flt.REVERSE_BITS_TABLE) == list(range(256))


def float_runner(start, condition, *, constraints=None):
    constraints = {} if constraints is None else constraints

    def test_function(data):
        f = data.draw_float(**constraints)
        if condition(f):
            data.mark_interesting()

    runner = ConjectureRunner(test_function)
    runner.cached_test_function((float(start),))
    assert runner.interesting_examples
    return runner


def minimal_from(start, condition, *, constraints=None):
    runner = float_runner(start, condition, constraints=constraints)
    runner.shrink_interesting_examples()
    (v,) = runner.interesting_examples.values()
    f = v.choices[0]
    assert condition(f)
    return f


INTERESTING_FLOATS = [0.0, 1.0, 2.0, sys.float_info.max, float("inf"), float("nan")]


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (a, b)
        for a in INTERESTING_FLOATS
        for b in INTERESTING_FLOATS
        if flt.float_to_lex(a) > flt.float_to_lex(b)
    ],
)
def test_can_shrink_downwards(start, end):
    assert minimal_from(start, lambda x: not (x < end)) == end


@pytest.mark.parametrize(
    "f", [1, 2, 4, 8, 10, 16, 32, 64, 100, 128, 256, 500, 512, 1000, 1024]
)
@pytest.mark.parametrize("mul", [1.1, 1.5, 9.99, 10])
def test_shrinks_downwards_to_integers(f, mul):
    g = minimal_from(f * mul, lambda x: x >= f)
    assert g == f


def test_shrink_to_integer_upper_bound():
    assert minimal_from(1.1, lambda x: 1 < x <= 2) == 2


def test_shrink_up_to_one():
    assert minimal_from(0.5, lambda x: 0.5 <= x <= 1.5) == 1


def test_shrink_down_to_half():
    assert minimal_from(0.75, lambda x: 0 < x < 1) == 0.5


def test_shrink_fractional_part():
    assert minimal_from(2.5, lambda x: divmod(x, 1)[1] == 0.5) == 1.5


def test_does_not_shrink_across_one():
    # This is something of an odd special case. Because of our encoding we
    # prefer all numbers >= 1 to all numbers in 0 < x < 1. For the most part
    # this is the correct thing to do, but there are some low negative exponent
    # cases where we get odd behaviour like this.

    # This test primarily exists to validate that we don't try to subtract one
    # from the starting point and trigger an internal exception.
    assert minimal_from(1.1, lambda x: x == 1.1 or 0 < x < 1) == 1.1


def test_reject_out_of_bounds_floats_while_shrinking():
    # coverage test for rejecting out of bounds floats while shrinking
    constraints = {"min_value": 103.0}
    g = minimal_from(103.1, lambda x: x >= 100, constraints=constraints)
    assert g == 103.0


@pytest.mark.parametrize("nan", [-math.nan, SIGNALING_NAN, -SIGNALING_NAN])
def test_shrinks_to_canonical_nan(nan):
    shrunk = minimal_from(nan, math.isnan)
    assert float_to_int(shrunk) == float_to_int(math.nan)
