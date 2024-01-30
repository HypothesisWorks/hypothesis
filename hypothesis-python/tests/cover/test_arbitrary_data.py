# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from pytest import raises

from hypothesis import find, given, strategies as st
from hypothesis.errors import InvalidArgument


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
            raise ValueError

    with raises(ValueError) as err:
        test()
    assert "Draw 1: [0, 0]" in err.value.__notes__
    assert "Draw 2: 0" in err.value.__notes__


def test_prints_labels_if_given_on_failure():
    @given(st.data())
    def test(data):
        x = data.draw(st.lists(st.integers(0, 10), min_size=2), label="Some numbers")
        y = data.draw(st.sampled_from(x), label="A number")
        assert y in x
        x.remove(y)
        assert y not in x

    with raises(AssertionError) as err:
        test()
    assert "Draw 1 (Some numbers): [0, 0]" in err.value.__notes__
    assert "Draw 2 (A number): 0" in err.value.__notes__


def test_given_twice_is_same():
    @given(st.data(), st.data())
    def test(data1, data2):
        data1.draw(st.integers())
        data2.draw(st.integers())
        raise ValueError

    with raises(ValueError) as err:
        test()
    assert "Draw 1: 0" in err.value.__notes__
    assert "Draw 2: 0" in err.value.__notes__


def test_errors_when_used_in_find():
    with raises(InvalidArgument):
        find(st.data(), lambda x: x.draw(st.booleans()))


@pytest.mark.parametrize("f", ["filter", "map", "flatmap"])
def test_errors_when_normal_strategy_functions_are_used(f):
    with raises(InvalidArgument):
        getattr(st.data(), f)(lambda x: 1)


def test_nice_repr():
    assert repr(st.data()) == "data()"
