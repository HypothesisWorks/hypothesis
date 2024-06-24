# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import sys
import typing

import pytest

from hypothesis import HealthCheck, assume, given, settings, strategies as st
from hypothesis.errors import (
    HypothesisDeprecationWarning,
    HypothesisWarning,
    InvalidArgument,
)

from tests.common.debug import minimal
from tests.common.utils import flaky


@st.composite
def badly_draw_lists(draw, m=0):
    length = draw(st.integers(m, m + 10))
    return [draw(st.integers()) for _ in range(length)]


def test_simplify_draws():
    assert minimal(badly_draw_lists(), lambda x: len(x) >= 3) == [0] * 3


def test_can_pass_through_arguments():
    assert minimal(badly_draw_lists(5)) == [0] * 5
    assert minimal(badly_draw_lists(m=6)) == [0] * 6


@st.composite
def draw_ordered_with_assume(draw):
    x = draw(st.floats())
    y = draw(st.floats())
    assume(x < y)
    return (x, y)


@given(draw_ordered_with_assume())
@settings(suppress_health_check=[HealthCheck.filter_too_much])
def test_can_assume_in_draw(xy):
    assert xy[0] < xy[1]


def test_uses_definitions_for_reprs():
    assert repr(badly_draw_lists()) == "badly_draw_lists()"
    assert repr(badly_draw_lists(1)) == "badly_draw_lists(m=1)"
    assert repr(badly_draw_lists(m=1)) == "badly_draw_lists(m=1)"


def test_errors_given_default_for_draw():
    with pytest.raises(InvalidArgument):

        @st.composite
        def foo(x=None):
            pass


def test_errors_given_function_of_no_arguments():
    with pytest.raises(InvalidArgument):

        @st.composite
        def foo():
            pass


def test_errors_given_kwargs_only():
    with pytest.raises(InvalidArgument):

        @st.composite
        def foo(**kwargs):
            pass


def test_warning_given_no_drawfn_call():
    with pytest.warns(HypothesisDeprecationWarning):

        @st.composite
        def foo(_):
            return "bar"


def test_can_use_pure_args():
    @st.composite
    def stuff(*args):
        return args[0](st.sampled_from(args[1:]))

    assert minimal(stuff(1, 2, 3, 4, 5)) == 1


def test_composite_of_lists():
    @st.composite
    def f(draw):
        return draw(st.integers()) + draw(st.integers())

    assert minimal(st.lists(f()), lambda x: len(x) >= 10) == [0] * 10


@flaky(min_passes=2, max_runs=5)
def test_can_shrink_matrices_with_length_param():
    @st.composite
    def matrix(draw):
        rows = draw(st.integers(1, 10))
        columns = draw(st.integers(1, 10))
        return [
            [draw(st.integers(0, 10000)) for _ in range(columns)] for _ in range(rows)
        ]

    def transpose(m):
        return [[row[i] for row in m] for i in range(len(m[0]))]

    def is_square(m):
        return len(m) == len(m[0])

    value = minimal(matrix(), lambda m: is_square(m) and transpose(m) != m)
    assert len(value) == 2
    assert len(value[0]) == 2
    assert sorted(value[0] + value[1]) == [0, 0, 0, 1]


class MyList(list):
    pass


@given(st.data(), st.lists(st.integers()).map(MyList))
def test_does_not_change_arguments(data, ls):
    # regression test for issue #1017 or other argument mutation
    @st.composite
    def strat(draw, arg):
        draw(st.none())
        return arg

    ex = data.draw(strat(ls))
    assert ex is ls


class ClsWithStrategyMethods:
    @classmethod
    @st.composite
    def st_classmethod_then_composite(draw, cls):
        return draw(st.integers(0, 10))

    @st.composite
    @classmethod
    def st_composite_then_classmethod(draw, cls):
        return draw(st.integers(0, 10))

    @staticmethod
    @st.composite
    def st_staticmethod_then_composite(draw):
        return draw(st.integers(0, 10))

    @st.composite
    @staticmethod
    def st_composite_then_staticmethod(draw):
        return draw(st.integers(0, 10))

    @st.composite
    def st_composite_method(draw, self):
        return draw(st.integers(0, 10))


@given(st.data())
def test_applying_composite_decorator_to_methods(data):
    instance = ClsWithStrategyMethods()
    for strategy in [
        ClsWithStrategyMethods.st_classmethod_then_composite(),
        ClsWithStrategyMethods.st_composite_then_classmethod(),
        ClsWithStrategyMethods.st_staticmethod_then_composite(),
        ClsWithStrategyMethods.st_composite_then_staticmethod(),
        instance.st_classmethod_then_composite(),
        instance.st_composite_then_classmethod(),
        instance.st_staticmethod_then_composite(),
        instance.st_composite_then_staticmethod(),
        instance.st_composite_method(),
    ]:
        x = data.draw(strategy)
        assert isinstance(x, int)
        assert 0 <= x <= 10


def test_drawfn_cannot_be_instantiated():
    with pytest.raises(TypeError):
        st.DrawFn()


@pytest.mark.skipif(sys.version_info[:2] == (3, 9), reason="stack depth varies???")
def test_warns_on_strategy_annotation():
    # TODO: print the stack on Python 3.10 and 3.11 to determine the appropriate
    #       stack depth to use.  Consider adding a debug-print if IN_COVERAGE_TESTS
    #       and the relevant depth is_hypothesis_file(), for easier future fixing.
    #
    # Meanwhile, the test is not skipped on 3.10/3.11 as it is still required for
    # coverage of the warning-generating branch.
    with pytest.warns(HypothesisWarning, match="Return-type annotation") as w:

        @st.composite
        def my_integers(draw: st.DrawFn) -> st.SearchStrategy[int]:
            return draw(st.integers())

    if sys.version_info[:2] > (3, 11):  # TEMP: see PR #3961
        assert len(w.list) == 1
        assert w.list[0].filename == __file__  # check stacklevel points to user code


def test_composite_allows_overload_without_draw():
    # See https://github.com/HypothesisWorks/hypothesis/issues/3970
    @st.composite
    @typing.overload
    def overloaded(draw: st.DrawFn, *, x: int) -> typing.Literal[True]: ...

    @st.composite
    @typing.overload
    def overloaded(draw: st.DrawFn, *, x: str) -> typing.Literal[False]: ...

    @st.composite
    def overloaded(draw: st.DrawFn, *, x: typing.Union[int, str]) -> bool:
        return draw(st.just(isinstance(x, int)))
