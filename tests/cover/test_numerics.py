# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

import decimal

import pytest

from hypothesis import given, assume, reject
from hypothesis.errors import InvalidArgument
from tests.common.debug import find_any
from hypothesis.strategies import data, none, tuples, decimals, integers, \
    fractions


@given(data())
def test_fuzz_fractions_bounds(data):
    denom = data.draw(none() | integers(1, 100), label='denominator')
    fracs = none() | fractions(max_denominator=denom)
    low, high = data.draw(tuples(fracs, fracs), label='low, high')
    if low is not None and high is not None and low > high:
        low, high = high, low
    try:
        val = data.draw(fractions(low, high, denom), label='value')
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
    places = data.draw(none() | integers(0, 20), label='places')
    finite_decs = decimals(allow_nan=False, allow_infinity=False,
                           places=places) | none()
    low, high = data.draw(tuples(finite_decs, finite_decs), label='low, high')
    if low is not None and high is not None and low > high:
        low, high = high, low
    ctx = decimal.Context(prec=data.draw(integers(1, 100), label='precision'))
    try:
        with decimal.localcontext(ctx):
            strat = decimals(low, high, allow_nan=False,
                             allow_infinity=False, places=places)
            val = data.draw(strat, label='value')
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
        decimals(),
        lambda x: assume(x.is_finite()) and decimal.Decimal(float(x)) == x
    )


@given(fractions(), fractions(), fractions())
def test_fraction_addition_is_well_behaved(x, y, z):
    assert x + y + z == y + x + z


def test_decimals_include_nan():
    find_any(decimals(), lambda x: x.is_nan())


def test_decimals_include_inf():
    find_any(decimals(), lambda x: x.is_infinite())


@given(decimals(allow_nan=False))
def test_decimals_can_disallow_nan(x):
    assert not x.is_nan()


@given(decimals(allow_infinity=False))
def test_decimals_can_disallow_inf(x):
    assert not x.is_infinite()


@pytest.mark.parametrize('places', range(10))
def test_decimals_have_correct_places(places):
    @given(decimals(0, 10, allow_nan=False, places=places))
    def inner_tst(n):
        assert n.as_tuple().exponent == -places
    inner_tst()


@given(decimals(min_value='0.1', max_value='0.2', allow_nan=False, places=1))
def test_works_with_few_values(dec):
    assert dec in (decimal.Decimal('0.1'), decimal.Decimal('0.2'))


@given(decimals(places=3, allow_nan=False, allow_infinity=False))
def test_issue_725_regression(x):
    pass


@given(decimals(min_value='0.1', max_value='0.3'))
def test_issue_739_regression(x):
    pass


def test_consistent_decimal_error():
    bad = 'invalid argument to Decimal'
    with pytest.raises(InvalidArgument) as excinfo:
        decimals(bad).example()
    with pytest.raises(InvalidArgument) as excinfo2:
        with decimal.localcontext(decimal.Context(traps=[])):
            decimals(bad).example()
    assert str(excinfo.value) == str(excinfo2.value)
