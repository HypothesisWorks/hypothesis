# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import functools
import warnings

import pytest

from hypothesis import find, given, strategies as st
from hypothesis.errors import HypothesisWarning, InvalidArgument
from hypothesis.internal.validation import check_type
from hypothesis.strategies import (
    SearchStrategy as ActualSearchStrategy,
    binary,
    booleans,
    data,
    dictionaries,
    floats,
    frozensets,
    integers,
    lists,
    nothing,
    recursive,
    sets,
    text,
)
from hypothesis.strategies._internal.strategies import check_strategy

from tests.common.debug import check_can_generate_examples, find_any
from tests.common.utils import fails_with


def test_errors_when_given_varargs():
    @given(integers())
    def has_varargs(*args):
        pass

    with pytest.raises(InvalidArgument) as e:
        has_varargs()
    assert "varargs" in e.value.args[0]


def test_varargs_without_positional_arguments_allowed():
    @given(somearg=integers())
    def has_varargs(somearg, *args):
        pass


def test_errors_when_given_varargs_and_kwargs_with_positional_arguments():
    @given(integers())
    def has_varargs(*args, **kw):
        pass

    with pytest.raises(InvalidArgument) as e:
        has_varargs()
    assert "varargs" in e.value.args[0]


def test_varargs_and_kwargs_without_positional_arguments_allowed():
    @given(somearg=integers())
    def has_varargs(*args, **kw):
        pass


def test_bare_given_errors():
    @given()
    def test():
        pass

    with pytest.raises(InvalidArgument):
        test()


def test_errors_on_unwanted_kwargs():
    @given(hello=int, world=int)
    def greet(world):
        pass

    with pytest.raises(InvalidArgument):
        greet()


def test_errors_on_too_many_positional_args():
    @given(integers(), int, int)
    def foo(x, y):
        pass

    with pytest.raises(InvalidArgument):
        foo()


def test_errors_on_any_varargs():
    @given(integers())
    def oops(*args):
        pass

    with pytest.raises(InvalidArgument):
        oops()


def test_can_put_arguments_in_the_middle():
    @given(y=integers())
    def foo(x, y, z):
        pass

    foo(1, 2)


def test_float_ranges():
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(floats(float("nan"), 0))
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(floats(1, -1))


def test_float_range_and_allow_nan_cannot_both_be_enabled():
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(floats(min_value=1, allow_nan=True))
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(floats(max_value=1, allow_nan=True))


def test_float_finite_range_and_allow_infinity_cannot_both_be_enabled():
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(floats(0, 1, allow_infinity=True))


def test_does_not_error_if_min_size_is_bigger_than_default_size():
    find_any(lists(integers(), min_size=50))
    find_any(sets(integers(), min_size=50))
    find_any(frozensets(integers(), min_size=50))
    find_any(lists(integers(), min_size=50, unique=True))


def test_list_unique_and_unique_by_cannot_both_be_enabled():
    @given(lists(integers(), unique=True, unique_by=lambda x: x))
    def boom(t):
        pass

    with pytest.raises(InvalidArgument) as e:
        boom()
    assert "unique " in e.value.args[0]
    assert "unique_by" in e.value.args[0]


def test_min_before_max():
    with pytest.raises(InvalidArgument):
        integers(min_value=1, max_value=0).validate()


def test_filter_validates():
    with pytest.raises(InvalidArgument):
        integers(min_value=1, max_value=0).filter(bool).validate()


def test_recursion_validates_base_case():
    with pytest.raises(InvalidArgument):
        recursive(integers(min_value=1, max_value=0), lists).validate()


def test_recursion_validates_recursive_step():
    with pytest.raises(InvalidArgument):
        recursive(integers(), lambda x: lists(x, min_size=3, max_size=1)).validate()


@fails_with(InvalidArgument)
@given(x=integers())
def test_stuff_keyword(x=1):
    pass


@fails_with(InvalidArgument)
@given(integers())
def test_stuff_positional(x=1):
    pass


@fails_with(InvalidArgument)
@given(integers(), integers())
def test_too_many_positional(x):
    pass


def test_given_warns_on_use_of_non_strategies():
    @given(bool)
    def test(x):
        pass

    with pytest.raises(InvalidArgument):
        test()


def test_given_warns_when_mixing_positional_with_keyword():
    @given(booleans(), y=booleans())
    def test(x, y):
        pass

    with pytest.raises(InvalidArgument):
        test()


def test_cannot_find_non_strategies():
    with pytest.raises(InvalidArgument):
        find(bool, bool)


@pytest.mark.parametrize(
    "strategy",
    [
        functools.partial(lists, elements=integers()),
        functools.partial(dictionaries, keys=integers(), values=integers()),
        text,
        binary,
    ],
)
@pytest.mark.parametrize("min_size,max_size", [(0, "10"), ("0", 10)])
def test_valid_sizes(strategy, min_size, max_size):
    @given(strategy(min_size=min_size, max_size=max_size))
    def test(x):
        pass

    with pytest.raises(InvalidArgument):
        test()


def test_check_type_with_tuple_of_length_two():
    def type_checker(x):
        check_type((int, str), x, "x")

    type_checker(1)
    type_checker("1")
    with pytest.raises(InvalidArgument, match="Expected one of int, str but got "):
        type_checker(1.0)


def test_validation_happens_on_draw():
    @given(data())
    def test(data):
        data.draw(integers().flatmap(lambda _: lists(nothing(), min_size=1)))

    with pytest.raises(InvalidArgument, match="has no values"):
        test()


class SearchStrategy:
    """Not the SearchStrategy type you were looking for."""


def check_type_(*args):
    return check_type(*args)


def test_check_type_suggests_check_strategy():
    check_type_(SearchStrategy, SearchStrategy(), "this is OK")
    with pytest.raises(AssertionError, match="use check_strategy instead"):
        check_type_(ActualSearchStrategy, None, "SearchStrategy assertion")


def check_strategy_(*args):
    return check_strategy(*args)


def test_check_strategy_might_suggest_sampled_from():
    with pytest.raises(InvalidArgument) as excinfo:
        check_strategy_("not a strategy")
    assert "sampled_from" not in str(excinfo.value)
    with pytest.raises(InvalidArgument, match="such as st.sampled_from"):
        check_strategy_([1, 2, 3])
    with pytest.raises(InvalidArgument, match="such as st.sampled_from"):
        check_strategy_((1, 2, 3))
    check_strategy_(integers(), "passes for our custom coverage check")


@pytest.mark.parametrize("codec", ["ascii", "utf-8"])
def test_warn_on_strings_matching_common_codecs(codec):
    with pytest.warns(
        HypothesisWarning,
        match=f"it seems like you are trying to use the codec {codec!r}",
    ):

        @given(st.text(codec))
        def f(s):
            pass

        f()

    # if we reorder, it doesn't warn anymore
    with warnings.catch_warnings():
        warnings.simplefilter("error")

        @given(st.text(codec[1:] + codec[:1]))
        def f(s):
            pass

        f()
