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

from hypothesis import HealthCheck, given, reject, settings, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.strategies import complex_numbers

from tests.common.debug import (
    assert_no_examples,
    check_can_generate_examples,
    find_any,
    minimal,
)


def test_minimal():
    assert minimal(complex_numbers()) == 0


def test_minimal_nonzero_real():
    assert minimal(complex_numbers(), lambda x: x.real != 0) == 1


def test_minimal_nonzero_imaginary():
    assert minimal(complex_numbers(), lambda x: x.imag != 0) == 1j


def test_minimal_quadrant1():
    assert minimal(complex_numbers(), lambda x: x.imag > 0 and x.real > 0) == 1 + 1j


def test_minimal_quadrant2():
    assert minimal(complex_numbers(), lambda x: x.imag > 0 and x.real < 0) == -1 + 1j


def test_minimal_quadrant3():
    assert minimal(complex_numbers(), lambda x: x.imag < 0 and x.real < 0) == -1 - 1j


def test_minimal_quadrant4():
    assert minimal(complex_numbers(), lambda x: x.imag < 0 and x.real > 0) == 1 - 1j


@given(st.data(), st.integers(-5, 5).map(lambda x: 10**x))
def test_max_magnitude_respected(data, mag):
    c = data.draw(complex_numbers(max_magnitude=mag))
    # Note we accept epsilon errors here as internally sqrt is used to draw
    # complex numbers. sqrt on some platforms gets epsilon errors, which is
    # too tricky to filter out and so - for now - we just accept them.
    assert abs(c) <= mag * (1 + sys.float_info.epsilon)


@given(complex_numbers(max_magnitude=0))
def test_max_magnitude_zero(val):
    assert val == 0


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(st.data(), st.integers(-5, 5).map(lambda x: 10**x))
def test_min_magnitude_respected(data, mag):
    c = data.draw(complex_numbers(min_magnitude=mag))
    # See test_max_magnitude_respected comment
    assert (
        abs(c.real) >= mag
        or abs(c.imag) >= mag
        or abs(c) >= mag * (1 - sys.float_info.epsilon)
    )


def test_minimal_min_magnitude_zero():
    assert minimal(complex_numbers(min_magnitude=0)) == 0


def test_minimal_min_magnitude_positive():
    assert minimal(complex_numbers(min_magnitude=0.5)) in (0.5, 1)


def test_minimal_minmax_magnitude():
    assert minimal(complex_numbers(min_magnitude=0.5, max_magnitude=1.5)) in (0.5, 1)


@given(st.data(), st.floats(0, 10e300, allow_infinity=False, allow_nan=False))
def test_minmax_magnitude_equal(data, mag):
    val = data.draw(st.complex_numbers(min_magnitude=mag, max_magnitude=mag))
    try:
        # Cap magnitude at 10e300 to avoid float overflow, and imprecision
        # at very large exponents (which makes math.isclose fail)
        assert math.isclose(abs(val), mag)
    except OverflowError:
        reject()


def _is_subnormal(x):
    return 0 < abs(x) < sys.float_info.min


@pytest.mark.parametrize(
    "allow_subnormal, min_magnitude, max_magnitude",
    [
        (True, 0, None),
        (True, 1, None),
        (False, 0, None),
    ],
)
def test_allow_subnormal(allow_subnormal, min_magnitude, max_magnitude):
    strat = complex_numbers(
        min_magnitude=min_magnitude,
        max_magnitude=max_magnitude,
        allow_subnormal=allow_subnormal,
    ).filter(lambda x: x.real != 0 and x.imag != 0)

    if allow_subnormal:
        find_any(strat, lambda x: _is_subnormal(x.real) or _is_subnormal(x.imag))
    else:
        assert_no_examples(
            strat, lambda x: _is_subnormal(x.real) or _is_subnormal(x.imag)
        )


@pytest.mark.parametrize("allow_subnormal", [1, 0.0, "False"])
def test_allow_subnormal_validation(allow_subnormal):
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(complex_numbers(allow_subnormal=allow_subnormal))
