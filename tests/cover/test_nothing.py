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

from hypothesis import given, strategies as st
from hypothesis.errors import InvalidArgument

from tests.common.debug import assert_no_examples, minimal


def test_resampling():
    x = minimal(
        st.lists(st.integers(), min_size=1).flatmap(
            lambda x: st.lists(st.sampled_from(x))
        ),
        lambda x: len(x) >= 10 and len(set(x)) == 1,
    )
    assert x == [0] * 10


@given(st.lists(st.nothing()))
def test_list_of_nothing(xs):
    assert xs == []


@given(st.sets(st.nothing()))
def test_set_of_nothing(xs):
    assert xs == set()


def test_validates_min_size():
    with pytest.raises(InvalidArgument):
        st.lists(st.nothing(), min_size=1).validate()


def test_function_composition():
    assert st.nothing().map(lambda x: "hi").is_empty
    assert st.nothing().filter(lambda x: True).is_empty
    assert st.nothing().flatmap(lambda x: st.integers()).is_empty


def test_tuples_detect_empty_elements():
    assert st.tuples(st.nothing()).is_empty


def test_fixed_dictionaries_detect_empty_values():
    assert st.fixed_dictionaries({"a": st.nothing()}).is_empty


def test_no_examples():
    assert_no_examples(st.nothing())


@pytest.mark.parametrize(
    "s",
    [
        st.nothing(),
        st.nothing().map(lambda x: x),
        st.nothing().filter(lambda x: True),
        st.nothing().flatmap(lambda x: st.integers()),
    ],
)
def test_empty(s):
    assert s.is_empty
