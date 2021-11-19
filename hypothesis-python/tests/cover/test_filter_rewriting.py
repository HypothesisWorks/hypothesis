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
from hypothesis.errors import HypothesisWarning, Unsatisfiable
from hypothesis.internal.reflection import get_pretty_function_description
from hypothesis.strategies._internal.lazy import LazyStrategy, unwrap_strategies
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
        # Simple lambdas
        (st.integers(), lambda x: x < 3, None, 2),
        (st.integers(), lambda x: x <= 3, None, 3),
        (st.integers(), lambda x: x == 3, 3, 3),
        (st.integers(), lambda x: x >= 3, 3, None),
        (st.integers(), lambda x: x > 3, 4, None),
        # Simple lambdas, reverse comparison
        (st.integers(), lambda x: 3 > x, None, 2),
        (st.integers(), lambda x: 3 >= x, None, 3),
        (st.integers(), lambda x: 3 == x, 3, 3),
        (st.integers(), lambda x: 3 <= x, 3, None),
        (st.integers(), lambda x: 3 < x, 4, None),
        # More complicated lambdas
        (st.integers(), lambda x: 0 < x < 5, 1, 4),
        (st.integers(), lambda x: 0 < x >= 1, 1, None),
        (st.integers(), lambda x: 1 > x <= 0, None, 0),
        (st.integers(), lambda x: x > 0 and x > 0, 1, None),
        (st.integers(), lambda x: x < 1 and x < 1, None, 0),
        (st.integers(), lambda x: x > 1 and x > 0, 2, None),
        (st.integers(), lambda x: x < 1 and x < 2, None, 0),
    ],
    ids=get_pretty_function_description,
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


Y = 2 ** 20


@given(
    data=st.data(),
    predicates=st.permutations(
        [
            partial(operator.lt, 1),
            partial(operator.le, 2),
            partial(operator.ge, 4),
            partial(operator.gt, 5),
            mod2,
            lambda x: x > 2 or x % 7,
            lambda x: 0 < x <= Y,
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
    for pred in unwrapped.flat_conditions:
        assert pred is mod2 or pred.__name__ == "<lambda>"


class NotAFunction:
    def __call__(self, bar):
        return True


lambda_without_source = eval("lambda x: x > 2", {}, {})
assert get_pretty_function_description(lambda_without_source) == "lambda x: <unknown>"


@pytest.mark.parametrize(
    "start, end, predicate",
    [
        (1, 4, lambda x: 0 < x < 5 and x % 7),
        (0, 9, lambda x: 0 <= x < 10 and x % 3),
        (1, None, lambda x: 0 < x <= Y),
        (None, None, lambda x: x == x),
        (None, None, lambda x: 1 == 1),
        (None, None, lambda x: 1 <= 2),
        (None, None, lambda x: x != 0),
        (None, None, NotAFunction()),
        (None, None, lambda_without_source),
        (None, None, lambda x, y=2: x >= 0),
    ],
)
@given(data=st.data())
def test_rewriting_partially_understood_filters(data, start, end, predicate):
    s = st.integers().filter(predicate).wrapped_strategy

    assert isinstance(s, FilteredStrategy)
    assert isinstance(s.filtered_strategy, IntegersStrategy)
    assert s.filtered_strategy.start == start
    assert s.filtered_strategy.end == end
    assert s.flat_conditions == (predicate,)

    value = data.draw(s)
    assert predicate(value)


@pytest.mark.parametrize(
    "strategy",
    [
        st.text(),
        st.text(min_size=2),
        st.lists(st.none()),
        st.lists(st.none(), min_size=2),
    ],
)
@pytest.mark.parametrize(
    "predicate",
    [bool, len, tuple, list, lambda x: x],
    ids=get_pretty_function_description,
)
def test_sequence_filter_rewriting(strategy, predicate):
    s = unwrap_strategies(strategy)
    fs = s.filter(predicate)
    assert not isinstance(fs, FilteredStrategy)
    if s.min_size > 0:
        assert fs is s
    else:
        assert fs.min_size == 1


@pytest.mark.parametrize("method", [str.lower, str.title, str.upper])
def test_warns_on_suspicious_string_methods(method):
    s = unwrap_strategies(st.text())
    with pytest.warns(
        HypothesisWarning, match="this allows all nonempty strings!  Did you mean"
    ):
        fs = s.filter(method)
    assert fs.min_size == 1


@pytest.mark.parametrize("method", [str.isidentifier, str.isalnum])
def test_bumps_min_size_and_filters_for_content_str_methods(method):
    s = unwrap_strategies(st.text())
    fs = s.filter(method)
    assert fs.filtered_strategy.min_size == 1
    assert fs.flat_conditions == (method,)
