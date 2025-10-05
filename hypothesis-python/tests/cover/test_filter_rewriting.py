# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import datetime as dt
import decimal
import math
import operator
import re
from fractions import Fraction
from functools import partial
from sys import float_info

import pytest

from hypothesis import HealthCheck, given, settings, strategies as st
from hypothesis.errors import HypothesisWarning, Unsatisfiable
from hypothesis.internal.conjecture.providers import COLLECTION_DEFAULT_MAX_SIZE
from hypothesis.internal.filtering import max_len, min_len
from hypothesis.internal.floats import next_down, next_up
from hypothesis.internal.reflection import get_pretty_function_description
from hypothesis.strategies._internal.core import data
from hypothesis.strategies._internal.lazy import LazyStrategy, unwrap_strategies
from hypothesis.strategies._internal.numbers import FloatStrategy, IntegersStrategy
from hypothesis.strategies._internal.strategies import FilteredStrategy, MappedStrategy
from hypothesis.strategies._internal.strings import BytesStrategy, TextStrategy

from tests.common.debug import check_can_generate_examples
from tests.common.utils import fails_with

A_FEW = 15  # speed up massively-parametrized tests


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
@settings(max_examples=A_FEW)
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
@settings(max_examples=A_FEW)
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
    check_can_generate_examples(s.filter(pred))


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
        check_can_generate_examples(s)


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
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_rewrite_filter_chains_with_some_unhandled(data, predicates, s):
    # Set up our strategy
    for p in predicates:
        s = s.filter(p)

    # Whatever value we draw is in fact valid for these strategies
    value = data.draw(s)
    for p in predicates:
        assert p(value), f"{p=}, value={value}"

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


@pytest.mark.parametrize("method", [str.isalnum])
def test_bumps_min_size_and_filters_for_content_str_methods(method):
    s = unwrap_strategies(st.text())
    fs = s.filter(method)
    assert fs.filtered_strategy.min_size == 1
    assert fs.flat_conditions == (method,)


# Should we deterministically check whether ascii or not or st.characters fine?
@pytest.mark.parametrize("al", [None, "cdef123", "cd12¥¦§©"])
@given(data())
def test_isidentifier_filter_properly_rewritten(al, data):
    if al is None:
        example = data.draw(st.text().filter(str.isidentifier))
    else:
        example = data.draw(st.text(alphabet=al).filter(str.isidentifier))
        assert set(example).issubset(al)
    assert example.isidentifier()


def test_isidentifer_filter_unsatisfiable():
    alphabet = "¥¦§©"
    assert not any(f"_{c}".isidentifier() for c in alphabet)
    fs = st.text(alphabet=alphabet).filter(str.isidentifier)
    with pytest.raises(Unsatisfiable):
        check_can_generate_examples(fs)


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


@pytest.mark.parametrize(
    "strategy, predicate, start, end",
    [
        # text with integer bounds
        (st.text(min_size=1, max_size=5), partial(min_len, 3), 3, 5),
        (st.text(min_size=1, max_size=5), partial(max_len, 3), 1, 3),
        # text with only one bound
        (st.text(min_size=1), partial(min_len, 3), 3, math.inf),
        (st.text(min_size=1), partial(max_len, 3), 1, 3),
        (st.text(max_size=5), partial(min_len, 3), 3, 5),
        (st.text(max_size=5), partial(max_len, 3), 0, 3),
        # Unbounded text
        (st.text(), partial(min_len, 3), 3, math.inf),
        (st.text(), partial(max_len, 3), 0, 3),
    ],
    ids=get_pretty_function_description,
)
@settings(max_examples=A_FEW)
@given(data=st.data())
def test_filter_rewriting_text_partial_len(data, strategy, predicate, start, end):
    s = strategy.filter(predicate)

    assert isinstance(s, LazyStrategy)
    inner = unwrap_strategies(s)
    assert isinstance(inner, TextStrategy)
    assert inner.min_size == start
    assert inner.max_size == end
    value = data.draw(s)
    assert predicate(value)


@given(data=st.data())
def test_can_rewrite_multiple_length_filters_if_not_lambdas(data):
    # This is a key capability for efficient rewriting using the `annotated-types`
    # package, although unfortunately we can't do it for lambdas.
    s = (
        st.text(min_size=1, max_size=5)
        .filter(partial(min_len, 2))
        .filter(partial(max_len, 4))
    )
    assert isinstance(s, LazyStrategy)
    inner = unwrap_strategies(s)
    assert isinstance(inner, TextStrategy)
    assert inner.min_size == 2
    assert inner.max_size == 4
    value = data.draw(s)
    assert 2 <= len(value) <= 4


@pytest.mark.parametrize(
    "predicate, start, end",
    [
        # Simple lambdas
        (lambda x: len(x) < 3, 0, 2),
        (lambda x: len(x) <= 3, 0, 3),
        (lambda x: len(x) == 3, 3, 3),
        (lambda x: len(x) >= 3, 3, math.inf),
        (lambda x: len(x) > 3, 4, math.inf),
        # Simple lambdas, reverse comparison
        (lambda x: 3 > len(x), 0, 2),
        (lambda x: 3 >= len(x), 0, 3),
        (lambda x: 3 == len(x), 3, 3),
        (lambda x: 3 <= len(x), 3, math.inf),
        (lambda x: 3 < len(x), 4, math.inf),
        # More complicated lambdas
        (lambda x: 0 < len(x) < 5, 1, 4),
        (lambda x: 0 < len(x) >= 1, 1, math.inf),
        (lambda x: 1 > len(x) <= 0, 0, 0),
        (lambda x: len(x) > 0 and len(x) > 0, 1, math.inf),
        (lambda x: len(x) < 1 and len(x) < 1, 0, 0),
        (lambda x: len(x) > 1 and len(x) > 0, 2, math.inf),
        (lambda x: len(x) < 1 and len(x) < 2, 0, 0),
    ],
    ids=get_pretty_function_description,
)
@pytest.mark.parametrize(
    "strategy",
    [
        st.text(),
        st.lists(st.integers()),
        st.lists(st.integers(), unique=True),
        st.lists(st.sampled_from([1, 2, 3])),
        st.binary(),
        st.sets(st.integers()),
        st.frozensets(st.integers()),
        st.dictionaries(st.integers(), st.none()),
        st.lists(st.integers(), unique_by=lambda x: x % 17).map(tuple),
    ],
    ids=get_pretty_function_description,
)
@settings(max_examples=A_FEW)
@given(data=st.data())
def test_filter_rewriting_text_lambda_len(data, strategy, predicate, start, end):
    s = strategy.filter(predicate)
    unwrapped_nofilter = unwrap_strategies(strategy)
    unwrapped = unwrap_strategies(s)

    if was_mapped := isinstance(unwrapped, MappedStrategy):
        unwrapped = unwrapped.mapped_strategy

    assert isinstance(unwrapped, FilteredStrategy), f"{unwrapped=} {type(unwrapped)=}"
    assert isinstance(
        unwrapped.filtered_strategy,
        type(unwrapped_nofilter.mapped_strategy if was_mapped else unwrapped_nofilter),
    )
    for pred in unwrapped.flat_conditions:
        assert pred.__name__ == "<lambda>"

    if isinstance(unwrapped.filtered_strategy, MappedStrategy):
        unwrapped = unwrapped.filtered_strategy.mapped_strategy

    # binary() has a finite-but-effectively-infinite cap instead.
    if isinstance(unwrapped_nofilter, BytesStrategy) and end == math.inf:
        end = COLLECTION_DEFAULT_MAX_SIZE

    assert unwrapped.filtered_strategy.min_size == start
    assert unwrapped.filtered_strategy.max_size == end
    value = data.draw(s)
    assert predicate(value)


two = 2


@pytest.mark.parametrize(
    "predicate, start, end",
    [
        # Simple lambdas
        (lambda x: len(x) < 3, 0, 2),
        (lambda x: len(x) <= 3, 0, 3),
        (lambda x: len(x) == 3, 3, 3),
        (lambda x: len(x) >= 3, 3, 3),  # input max element_count=3
        # Simple lambdas, reverse comparison
        (lambda x: 3 > len(x), 0, 2),
        (lambda x: 3 >= len(x), 0, 3),
        (lambda x: 3 == len(x), 3, 3),
        (lambda x: 3 <= len(x), 3, 3),  # input max element_count=3
        # More complicated lambdas
        (lambda x: 0 < len(x) < 5, 1, 3),  # input max element_count=3
        (lambda x: 0 < len(x) >= 1, 1, 3),  # input max element_count=3
        (lambda x: 1 > len(x) <= 0, 0, 0),
        (lambda x: len(x) > 0 and len(x) > 0, 1, 3),  # input max element_count=3
        (lambda x: len(x) < 1 and len(x) < 1, 0, 0),
        (lambda x: len(x) > 1 and len(x) > 0, 2, 3),  # input max element_count=3
        (lambda x: len(x) < 1 and len(x) < 2, 0, 0),
        # Comparisons involving one literal and one variable
        (lambda x: 1 <= len(x) <= two, 1, 3),
        (lambda x: two <= len(x) <= 4, 0, 3),
    ],
    ids=get_pretty_function_description,
)
@pytest.mark.parametrize(
    "strategy",
    [
        st.lists(st.sampled_from([1, 2, 3]), unique=True),
    ],
    ids=get_pretty_function_description,
)
@settings(max_examples=A_FEW)
@given(data=st.data())
def test_filter_rewriting_lambda_len_unique_elements(
    data, strategy, predicate, start, end
):
    s = strategy.filter(predicate)
    unwrapped = unwrap_strategies(s)
    assert isinstance(unwrapped, FilteredStrategy)
    assert isinstance(unwrapped.filtered_strategy, type(unwrap_strategies(strategy)))
    for pred in unwrapped.flat_conditions:
        assert pred.__name__ == "<lambda>"

    assert unwrapped.filtered_strategy.min_size == start
    assert unwrapped.filtered_strategy.max_size == end
    value = data.draw(s)
    assert predicate(value)


@pytest.mark.parametrize(
    "predicate",
    [
        (lambda x: len(x) < 3),
        (lambda x: len(x) > 5),
    ],
    ids=get_pretty_function_description,
)
def test_does_not_rewrite_unsatisfiable_len_filter(predicate):
    strategy = st.lists(st.none(), min_size=4, max_size=4).filter(predicate)
    with pytest.raises(Unsatisfiable):
        check_can_generate_examples(strategy)
    # Rewriting to nothing() would correctly express the constraint.  However
    # we don't want _only rewritable strategies_ to work in e.g. one_of, so:
    assert not strategy.is_empty


@pytest.mark.parametrize(
    "method", ["match", "search", "findall", "fullmatch", "finditer", "split"]
)
@pytest.mark.parametrize(
    "strategy, pattern",
    [
        (st.text(), "ab+c"),
        (st.text(), "a|b"),
        (st.text(alphabet="abcdef"), "ab+c"),
        (st.text(min_size=5, max_size=10), "ab+c"),
        (st.binary(), b"ab+c"),
        (st.binary(), b"a|b"),
        (st.binary(min_size=5, max_size=10), b"ab+c"),
    ],
    ids=repr,
)
@settings(max_examples=A_FEW)
@given(data=st.data())
def test_regex_filter_rewriting(data, strategy, pattern, method):
    # This would raise a HealthCheck without rewriting, so checking that
    # we can draw a valid value is sufficient.
    predicate = getattr(re.compile(pattern), method)
    s = strategy.filter(predicate)
    if method in ("finditer", "split"):
        msg = r"You applied re.compile\(.+?\).\w+ as a filter, but this allows"
        with pytest.warns(HypothesisWarning, match=msg):
            value = data.draw(s)
    else:
        value = data.draw(s)
    assert predicate(value)


@fails_with(TypeError)
@given(st.text().filter(re.compile("abc").sub))
def test_error_on_method_which_requires_multiple_args(_):
    pass


def test_dates_filter_rewriting():
    today = dt.date.today()

    assert st.dates().filter(partial(operator.lt, dt.date.max)).is_empty
    assert st.dates().filter(partial(operator.gt, dt.date.min)).is_empty
    assert st.dates(min_value=today).filter(partial(operator.gt, today)).is_empty
    assert st.dates(max_value=today).filter(partial(operator.lt, today)).is_empty

    bare = unwrap_strategies(st.dates())
    assert bare.filter(partial(operator.ge, dt.date.max)) is bare
    assert bare.filter(partial(operator.le, dt.date.min)) is bare

    new = bare.filter(partial(operator.le, today))
    assert not new.is_empty
    assert new is not bare
