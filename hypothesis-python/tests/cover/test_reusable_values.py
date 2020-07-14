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

from hypothesis import example, given, reject, strategies as st
from hypothesis.errors import HypothesisDeprecationWarning, InvalidArgument

base_reusable_strategies = (
    st.text(),
    st.binary(),
    st.dates(),
    st.times(),
    st.timedeltas(),
    st.booleans(),
    st.complex_numbers(),
    st.floats(),
    st.floats(-1.0, 1.0),
    st.integers(),
    st.integers(1, 10),
    st.integers(1),
)


@st.deferred
def reusable():
    return st.one_of(
        st.sampled_from(base_reusable_strategies),
        st.builds(
            st.floats,
            min_value=st.none() | st.floats(),
            max_value=st.none() | st.floats(),
            allow_infinity=st.booleans(),
            allow_nan=st.booleans(),
        ),
        st.builds(st.just, st.builds(list)),
        st.builds(st.sampled_from, st.lists(st.builds(list), min_size=1)),
        st.lists(reusable).map(st.one_of),
        st.lists(reusable).map(lambda ls: st.tuples(*ls)),
    )


assert not reusable.is_empty


@example(st.integers(min_value=1))
@given(reusable)
def test_reusable_strategies_are_all_reusable(s):
    try:
        s.validate()
    except (InvalidArgument, HypothesisDeprecationWarning):
        reject()

    assert s.has_reusable_values


for s in base_reusable_strategies:
    test_reusable_strategies_are_all_reusable = example(s)(
        test_reusable_strategies_are_all_reusable
    )
    test_reusable_strategies_are_all_reusable = example(st.tuples(s))(
        test_reusable_strategies_are_all_reusable
    )


def test_composing_breaks_reusability():
    s = st.integers()
    assert s.has_reusable_values
    assert not s.filter(lambda x: True).has_reusable_values
    assert not s.map(lambda x: x).has_reusable_values
    assert not s.flatmap(lambda x: st.just(x)).has_reusable_values


@pytest.mark.parametrize(
    "strat",
    [
        st.lists(st.booleans()),
        st.sets(st.booleans()),
        st.dictionaries(st.booleans(), st.booleans()),
    ],
)
def test_mutable_collections_do_not_have_reusable_values(strat):
    assert not strat.has_reusable_values


def test_recursion_does_not_break_reusability():
    x = st.deferred(lambda: st.none() | st.tuples(x))
    assert x.has_reusable_values
