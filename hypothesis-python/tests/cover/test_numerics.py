# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import decimal
from math import copysign, inf

import pytest

from hypothesis import HealthCheck, assume, given, reject, settings
from hypothesis.errors import InvalidArgument
from hypothesis.internal.floats import next_down, next_up
from hypothesis.strategies import (
    booleans,
    data,
    decimals,
    floats,
    fractions,
    integers,
    none,
    sampled_from,
    tuples,
)

from tests.common.debug import check_can_generate_examples, find_any


@settings(suppress_health_check=list(HealthCheck))
@given(data())
def test_fuzz_floats_bounds(data):
    width = data.draw(sampled_from([64, 32, 16]))
    bound = none() | floats(allow_nan=False, width=width)
    low, high = data.draw(tuples(bound, bound), label="low, high")
    if low is not None and high is not None and low > high:
        low, high = high, low
    if low is not None and high is not None and low > high:
        low, high = high, low
    exmin = low is not None and low != inf and data.draw(booleans(), label="ex_min")
    exmax = high is not None and high != -inf and data.draw(booleans(), label="ex_max")

    if low is not None and high is not None:
        lo = next_up(low, width) if exmin else low
        hi = next_down(high, width) if exmax else high
        # There must actually be floats between these bounds
        assume(lo <= hi)
        if lo == hi == 0:
            assume(not exmin and not exmax and copysign(1.0, lo) <= copysign(1.0, hi))

    s = floats(low, high, exclude_min=exmin, exclude_max=exmax, width=width)
    val = data.draw(s, label="value")
    assume(val)  # positive/negative zero is an issue

    if low is not None:
        assert low <= val
    if high is not None:
        assert val <= high
    if exmin:
        assert low != val
    if exmax:
        assert high != val


@given(data())
def test_fuzz_fractions_bounds(data):
    denom = data.draw(none() | integers(1, 100), label="denominator")
    fracs = none() | fractions(max_denominator=denom)
    low, high = data.draw(tuples(fracs, fracs), label="low, high")
    if low is not None and high is not None and low > high:
        low, high = high, low
    try:
        val = data.draw(fractions(low, high, max_denominator=denom), label="value")
    except InvalidArgument:
        reject()  # fractions too close for given max_denominator
    if low is not None:
        assert low <= val
    if high is not None:
        assert val <= high
    if denom is not None:
        assert 1 <= val.denominator <= denom


@given(data())
def test_fuzz_decimals_bounds(data):
    places = data.draw(none() | integers(0, 20), label="places")
    finite_decs = (
        decimals(allow_nan=False, allow_infinity=False, places=places) | none()
    )
    low, high = data.draw(tuples(finite_decs, finite_decs), label="low, high")
    if low is not None and high is not None and low > high:
        low, high = high, low
    ctx = decimal.Context(prec=data.draw(integers(1, 100), label="precision"))
    try:
        with decimal.localcontext(ctx):
            strat = decimals(
                low, high, allow_nan=False, allow_infinity=False, places=places
            )
            val = data.draw(strat, label="value")
    except InvalidArgument:
        reject()  # decimals too close for given places
    if low is not None:
        assert low <= val
    if high is not None:
        assert val <= high
    if places is not None:
        assert val.as_tuple().exponent == -places


def test_all_decimals_can_be_exact_floats():
    find_any(
        decimals(), lambda x: assume(x.is_finite()) and decimal.Decimal(float(x)) == x
    )


@given(fractions(), fractions(), fractions())
def test_fraction_addition_is_well_behaved(x, y, z):
    assert x + y + z == y + x + z


def test_decimals_include_nan():
    find_any(decimals(), lambda x: x.is_nan())


def test_decimals_include_inf():
    find_any(decimals(), lambda x: x.is_infinite(), settings(max_examples=10**6))


@given(decimals(allow_nan=False))
def test_decimals_can_disallow_nan(x):
    assert not x.is_nan()


@given(decimals(allow_infinity=False))
def test_decimals_can_disallow_inf(x):
    assert not x.is_infinite()


@pytest.mark.parametrize("places", range(10))
def test_decimals_have_correct_places(places):
    @given(decimals(0, 10, allow_nan=False, places=places))
    def inner_tst(n):
        assert n.as_tuple().exponent == -places

    inner_tst()


@given(decimals(min_value="0.1", max_value="0.2", allow_nan=False, places=1))
def test_works_with_few_values(dec):
    assert dec in (decimal.Decimal("0.1"), decimal.Decimal("0.2"))


@given(decimals(places=3, allow_nan=False, allow_infinity=False))
def test_issue_725_regression(x):
    pass


@given(decimals(min_value="0.1", max_value="0.3"))
def test_issue_739_regression(x):
    pass


def test_consistent_decimal_error():
    bad = "invalid argument to Decimal"
    with pytest.raises(InvalidArgument) as excinfo:
        check_can_generate_examples(decimals(bad))
    with pytest.raises(InvalidArgument) as excinfo2:
        with decimal.localcontext(decimal.Context(traps=[])):
            check_can_generate_examples(decimals(bad))
    assert str(excinfo.value) == str(excinfo2.value)


@pytest.mark.parametrize(
    "s, msg",
    [
        (
            floats(min_value=inf, allow_infinity=False),
            "allow_infinity=False excludes min_value=inf",
        ),
        (
            floats(min_value=next_down(inf), exclude_min=True, allow_infinity=False),
            "exclude_min=True turns min_value=.+? into inf, but allow_infinity=False",
        ),
        (
            floats(max_value=-inf, allow_infinity=False),
            "allow_infinity=False excludes max_value=-inf",
        ),
        (
            floats(max_value=next_up(-inf), exclude_max=True, allow_infinity=False),
            "exclude_max=True turns max_value=.+? into -inf, but allow_infinity=False",
        ),
    ],
)
def test_floats_message(s, msg):
    # https://github.com/HypothesisWorks/hypothesis/issues/3207
    with pytest.raises(InvalidArgument, match=msg):
        s.validate()
