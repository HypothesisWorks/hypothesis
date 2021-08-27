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

import pytest

from hypothesis import assume, given, strategies as st
from hypothesis.errors import InvalidArgument

from tests.common.debug import minimal
from tests.common.utils import flaky


@st.composite
def badly_draw_lists(draw, m=0):
    length = draw(st.integers(m, m + 10))
    return [draw(st.integers()) for _ in range(length)]


def test_simplify_draws():
    assert minimal(badly_draw_lists(), lambda x: len(x) >= 3) == [0] * 3


def test_can_pass_through_arguments():
    assert minimal(badly_draw_lists(5), lambda x: True) == [0] * 5
    assert minimal(badly_draw_lists(m=6), lambda x: True) == [0] * 6


@st.composite
def draw_ordered_with_assume(draw):
    x = draw(st.floats())
    y = draw(st.floats())
    assume(x < y)
    return (x, y)


@given(draw_ordered_with_assume())
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


def test_can_use_pure_args():
    @st.composite
    def stuff(*args):
        return args[0](st.sampled_from(args[1:]))

    assert minimal(stuff(1, 2, 3, 4, 5), lambda x: True) == 1


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
