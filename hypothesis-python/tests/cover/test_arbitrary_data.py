# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

from hypothesis import find, given, reporting, strategies as st
from hypothesis.errors import InvalidArgument
from tests.common.utils import capture_out, raises


@given(st.integers(), st.data())
def test_conditional_draw(x, data):
    y = data.draw(st.integers(min_value=x))
    assert y >= x


def test_prints_on_failure():
    @given(st.data())
    def test(data):
        x = data.draw(st.lists(st.integers(0, 10), min_size=2))
        y = data.draw(st.sampled_from(x))
        x.remove(y)
        if y in x:
            raise ValueError()

    with raises(ValueError):
        with capture_out() as out:
            with reporting.with_reporter(reporting.default):
                test()
    result = out.getvalue()
    assert "Draw 1: [0, 0]" in result
    assert "Draw 2: 0" in result


def test_prints_labels_if_given_on_failure():
    @given(st.data())
    def test(data):
        x = data.draw(st.lists(st.integers(0, 10), min_size=2), label="Some numbers")
        y = data.draw(st.sampled_from(x), label="A number")
        assert y in x
        x.remove(y)
        assert y not in x

    with raises(AssertionError):
        with capture_out() as out:
            with reporting.with_reporter(reporting.default):
                test()
    result = out.getvalue()
    assert "Draw 1 (Some numbers): [0, 0]" in result
    assert "Draw 2 (A number): 0" in result


def test_given_twice_is_same():
    @given(st.data(), st.data())
    def test(data1, data2):
        data1.draw(st.integers())
        data2.draw(st.integers())
        raise ValueError()

    with raises(ValueError):
        with capture_out() as out:
            with reporting.with_reporter(reporting.default):
                test()
    result = out.getvalue()
    assert "Draw 1: 0" in result
    assert "Draw 2: 0" in result


def test_errors_when_used_in_find():
    with raises(InvalidArgument):
        find(st.data(), lambda x: x.draw(st.booleans()))


@pytest.mark.parametrize("f", ["filter", "map", "flatmap"])
def test_errors_when_normal_strategy_functions_are_used(f):
    with raises(InvalidArgument):
        getattr(st.data(), f)(lambda x: 1)


def test_errors_when_asked_for_example():
    with raises(InvalidArgument):
        st.data().example()


def test_nice_repr():
    assert repr(st.data()) == "data()"
