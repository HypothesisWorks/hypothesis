# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
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

import decimal
import math
import operator
from functools import partial

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import Unsatisfiable
from hypothesis.strategies._internal.lazy import LazyStrategy
from hypothesis.strategies._internal.numbers import IntegersStrategy
from hypothesis.strategies._internal.strategies import FilteredStrategy

from tests.common.utils import fails_with


@pytest.mark.parametrize(
    "strategy, predicate, start, end",
    [
        # Integers with integer bounds
        (st.integers(1, 5), partial(operator.lt, 3), 4, 5),  # lambda x: 3 < x
        (st.integers(1, 5), partial(operator.le, 3), 3, 5),  # lambda x: 3 <= x
        (st.integers(1, 5), partial(operator.eq, 3), 3, 3),  # lambda x: 3 == x
        (st.integers(1, 5), partial(operator.ge, 3), 1, 3),  # lambda x: 3 >= x
        (st.integers(1, 5), partial(operator.gt, 3), 1, 2),  # lambda x: 3 > x
        # Integers with non-integer bounds
        (st.integers(1, 5), partial(operator.lt, 3.5), 4, 5),
        (st.integers(1, 5), partial(operator.le, 3.5), 4, 5),
        (st.integers(1, 5), partial(operator.ge, 3.5), 1, 3),
        (st.integers(1, 5), partial(operator.gt, 3.5), 1, 3),
        (st.integers(1, 5), partial(operator.lt, -math.inf), 1, 5),
        (st.integers(1, 5), partial(operator.gt, math.inf), 1, 5),
        # Integers with only one bound
        (st.integers(min_value=1), partial(operator.lt, 3), 4, None),
        (st.integers(min_value=1), partial(operator.le, 3), 3, None),
        (st.integers(max_value=5), partial(operator.ge, 3), None, 3),
        (st.integers(max_value=5), partial(operator.gt, 3), None, 2),
        # Unbounded integers
        (st.integers(), partial(operator.lt, 3), 4, None),
        (st.integers(), partial(operator.le, 3), 3, None),
        (st.integers(), partial(operator.eq, 3), 3, 3),
        (st.integers(), partial(operator.ge, 3), None, 3),
        (st.integers(), partial(operator.gt, 3), None, 2),
    ],
)
@given(data=st.data())
def test_filter_rewriting(data, strategy, predicate, start, end):
    s = strategy.filter(predicate)
    assert isinstance(s, LazyStrategy)
    assert isinstance(s.wrapped_strategy, IntegersStrategy)
    assert s.wrapped_strategy.start == start
    assert s.wrapped_strategy.end == end
    value = data.draw(s)
    assert predicate(value)


@pytest.mark.parametrize(
    "s",
    [
        st.integers(1, 5).filter(partial(operator.lt, 6)),
        st.integers(1, 5).filter(partial(operator.eq, 3.5)),
        st.integers(1, 5).filter(partial(operator.eq, "can't compare to strings")),
        st.integers(1, 5).filter(partial(operator.ge, 0)),
        st.integers(1, 5).filter(partial(operator.lt, math.inf)),
        st.integers(1, 5).filter(partial(operator.gt, -math.inf)),
    ],
)
@fails_with(Unsatisfiable)
@given(data=st.data())
def test_rewrite_unsatisfiable_filter(data, s):
    data.draw(s)


@given(st.integers(0, 2).filter(partial(operator.ne, 1)))
def test_unhandled_operator(x):
    assert x in (0, 2)


def test_rewriting_does_not_compare_decimal_snan():
    s = st.integers(1, 5).filter(partial(operator.eq, decimal.Decimal("snan")))
    s.wrapped_strategy
    with pytest.raises(decimal.InvalidOperation):
        s.example()


@pytest.mark.parametrize(
    "strategy, lo, hi",
    [
        (st.integers(0, 1), -1, 2),
    ],
    ids=repr,
)
def test_applying_noop_filter_returns_self(strategy, lo, hi):
    s = strategy.wrapped_strategy
    s2 = s.filter(partial(operator.le, -1)).filter(partial(operator.ge, 2))
    assert s is s2


def mod2(x):
    return x % 2


@given(
    data=st.data(),
    predicates=st.permutations(
        [
            partial(operator.lt, 1),
            partial(operator.le, 2),
            partial(operator.ge, 4),
            partial(operator.gt, 5),
            mod2,
        ]
    ),
)
def test_rewrite_filter_chains_with_some_unhandled(data, predicates):
    # Set up our strategy
    s = st.integers(1, 5)
    for p in predicates:
        s = s.filter(p)

    # Whatever value we draw is in fact valid for these strategies
    value = data.draw(s)
    for p in predicates:
        assert p(value), f"p={p!r}, value={value}"

    # No matter the order of the filters, we get the same resulting structure
    unwrapped = s.wrapped_strategy
    assert isinstance(unwrapped, FilteredStrategy)
    assert isinstance(unwrapped.filtered_strategy, IntegersStrategy)
    assert unwrapped.flat_conditions == (mod2,)
