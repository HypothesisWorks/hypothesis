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
import math
import operator
from fractions import Fraction
from functools import partial
from sys import float_info

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import HypothesisWarning, Unsatisfiable
from hypothesis.internal.floats import next_down, next_up
from hypothesis.internal.reflection import get_pretty_function_description
from hypothesis.strategies._internal.lazy import LazyStrategy, unwrap_strategies
from hypothesis.strategies._internal.numbers import FloatStrategy, IntegersStrategy
from hypothesis.strategies._internal.strategies import FilteredStrategy

from tests.common.utils import fails_with


@pytest.mark.parametrize(
    "strategy, predicate, start, end",
    [
        # Finitude check
        (st.integers(1, 5), math.isfinite, 1, 5),
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
def test_filter_rewriting_ints(data, strategy, predicate, start, end):
    s = strategy.filter(predicate)
    assert isinstance(s, LazyStrategy)
    assert isinstance(s.wrapped_strategy, IntegersStrategy)
    assert s.wrapped_strategy.start == start
    assert s.wrapped_strategy.end == end
    value = data.draw(s)
    assert predicate(value)


@pytest.mark.parametrize(
    "strategy, predicate, min_value, max_value",
    [
        # Floats with integer bounds
        (st.floats(1, 5), partial(operator.lt, 3), next_up(3.0), 5),  # 3 < x
        (st.floats(1, 5), partial(operator.le, 3), 3, 5),  # lambda x: 3 <= x
        (st.floats(1, 5), partial(operator.eq, 3), 3, 3),  # lambda x: 3 == x
        (st.floats(1, 5), partial(operator.ge, 3), 1, 3),  # lambda x: 3 >= x
        (st.floats(1, 5), partial(operator.gt, 3), 1, next_down(3.0)),  # 3 > x
        # Floats with non-integer bounds
        (st.floats(1, 5), partial(operator.lt, 3.5), next_up(3.5), 5),
        (st.floats(1, 5), partial(operator.le, 3.5), 3.5, 5),
        (st.floats(1, 5), partial(operator.ge, 3.5), 1, 3.5),
        (st.floats(1, 5), partial(operator.gt, 3.5), 1, next_down(3.5)),
        (st.floats(1, 5), partial(operator.lt, -math.inf), 1, 5),
        (st.floats(1, 5), partial(operator.gt, math.inf), 1, 5),
        # Floats with only one bound
        (st.floats(min_value=1), partial(operator.lt, 3), next_up(3.0), math.inf),
        (st.floats(min_value=1), partial(operator.le, 3), 3, math.inf),
        (st.floats(max_value=5), partial(operator.ge, 3), -math.inf, 3),
        (st.floats(max_value=5), partial(operator.gt, 3), -math.inf, next_down(3.0)),
        # Unbounded floats
        (st.floats(), partial(operator.lt, 3), next_up(3.0), math.inf),
        (st.floats(), partial(operator.le, 3), 3, math.inf),
        (st.floats(), partial(operator.eq, 3), 3, 3),
        (st.floats(), partial(operator.ge, 3), -math.inf, 3),
        (st.floats(), partial(operator.gt, 3), -math.inf, next_down(3.0)),
        # Simple lambdas
        (st.floats(), lambda x: x < 3, -math.inf, next_down(3.0)),
        (st.floats(), lambda x: x <= 3, -math.inf, 3),
        (st.floats(), lambda x: x == 3, 3, 3),
        (st.floats(), lambda x: x >= 3, 3, math.inf),
        (st.floats(), lambda x: x > 3, next_up(3.0), math.inf),
        # Simple lambdas, reverse comparison
        (st.floats(), lambda x: 3 > x, -math.inf, next_down(3.0)),
        (st.floats(), lambda x: 3 >= x, -math.inf, 3),
        (st.floats(), lambda x: 3 == x, 3, 3),
        (st.floats(), lambda x: 3 <= x, 3, math.inf),
        (st.floats(), lambda x: 3 < x, next_up(3.0), math.inf),
        # More complicated lambdas
        (st.floats(), lambda x: 0 < x < 5, next_up(0.0), next_down(5.0)),
        (st.floats(), lambda x: 0 < x >= 1, 1, math.inf),
        (st.floats(), lambda x: 1 > x <= 0, -math.inf, 0),
        (st.floats(), lambda x: x > 0 and x > 0, next_up(0.0), math.inf),
        (st.floats(), lambda x: x < 1 and x < 1, -math.inf, next_down(1.0)),
        (st.floats(), lambda x: x > 1 and x > 0, next_up(1.0), math.inf),
        (st.floats(), lambda x: x < 1 and x < 2, -math.inf, next_down(1.0)),
        # Specific named functions
        (st.floats(), math.isfinite, next_up(-math.inf), next_down(math.inf)),
    ],
    ids=get_pretty_function_description,
)
@given(data=st.data())
def test_filter_rewriting_floats(data, strategy, predicate, min_value, max_value):
    s = strategy.filter(predicate)
    assert isinstance(s, LazyStrategy)
    assert isinstance(s.wrapped_strategy, FloatStrategy)
    assert s.wrapped_strategy.min_value == min_value
    assert s.wrapped_strategy.max_value == max_value
    value = data.draw(s)
    assert predicate(value)


@pytest.mark.parametrize(
    "pred",
    [
        math.isinf,
        math.isnan,
        partial(operator.lt, 6),
        partial(operator.eq, Fraction(10, 3)),
        partial(operator.ge, 0),
        partial(operator.lt, math.inf),
        partial(operator.gt, -math.inf),
    ],
)
@pytest.mark.parametrize("s", [st.integers(1, 5), st.floats(1, 5)])
def test_rewrite_unsatisfiable_filter(s, pred):
    assert s.filter(pred).is_empty


@pytest.mark.parametrize(
    "pred",
    [
        partial(operator.eq, "numbers are never equal to strings"),
    ],
)
@pytest.mark.parametrize("s", [st.integers(1, 5), st.floats(1, 5)])
@fails_with(Unsatisfiable)
def test_erroring_rewrite_unsatisfiable_filter(s, pred):
    s.filter(pred).example()


@pytest.mark.parametrize(
    "strategy, predicate",
    [
        (st.floats(), math.isinf),
        (st.floats(0, math.inf), math.isinf),
        (st.floats(), math.isnan),
    ],
)
@given(data=st.data())
def test_misc_sat_filter_rewrites(data, strategy, predicate):
    s = strategy.filter(predicate).wrapped_strategy
    assert not isinstance(s, FloatStrategy)
    value = data.draw(s)
    assert predicate(value)


@pytest.mark.parametrize(
    "strategy, predicate",
    [
        (st.floats(allow_infinity=False), math.isinf),
        (st.floats(0, math.inf), math.isnan),
        (st.floats(allow_nan=False), math.isnan),
    ],
)
@given(data=st.data())
def test_misc_unsat_filter_rewrites(data, strategy, predicate):
    assert strategy.filter(predicate).is_empty


@given(st.integers(0, 2).filter(partial(operator.ne, 1)))
def test_unhandled_operator(x):
    assert x in (0, 2)


def test_rewriting_does_not_compare_decimal_snan():
    s = st.integers(1, 5).filter(partial(operator.eq, decimal.Decimal("snan")))
    s.wrapped_strategy
    with pytest.raises(decimal.InvalidOperation):
        s.example()


@pytest.mark.parametrize("strategy", [st.integers(0, 1), st.floats(0, 1)], ids=repr)
def test_applying_noop_filter_returns_self(strategy):
    s = strategy.wrapped_strategy
    s2 = s.filter(partial(operator.le, -1)).filter(partial(operator.ge, 2))
    assert s is s2


def mod2(x):
    return x % 2


Y = 2**20


@pytest.mark.parametrize("s", [st.integers(1, 5), st.floats(1, 5)])
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
def test_rewrite_filter_chains_with_some_unhandled(data, predicates, s):
    # Set up our strategy
    for p in predicates:
        s = s.filter(p)

    # Whatever value we draw is in fact valid for these strategies
    value = data.draw(s)
    for p in predicates:
        assert p(value), f"p={p!r}, value={value}"

    # No matter the order of the filters, we get the same resulting structure
    unwrapped = s.wrapped_strategy
    assert isinstance(unwrapped, FilteredStrategy)
    assert isinstance(unwrapped.filtered_strategy, (IntegersStrategy, FloatStrategy))
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


@pytest.mark.parametrize(
    "op, attr, value, expected",
    [
        (operator.lt, "min_value", -float_info.min / 2, 0),
        (operator.lt, "min_value", float_info.min / 2, float_info.min),
        (operator.gt, "max_value", float_info.min / 2, 0),
        (operator.gt, "max_value", -float_info.min / 2, -float_info.min),
    ],
)
def test_filter_floats_can_skip_subnormals(op, attr, value, expected):
    base = st.floats(allow_subnormal=False).filter(partial(op, value))
    assert getattr(base.wrapped_strategy, attr) == expected
