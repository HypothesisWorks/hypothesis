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

from hypothesis import example, given, strategies as st
from hypothesis.errors import InvalidArgument

# Be aware that tests in this file pass strategies as arguments to @example.
# That's normally a mistake, but for these tests it's intended.
# If one of these tests fails, Hypothesis will complain about the
# @example/strategy interaction, but it should be safe to ignore that
# error message and focus on the underlying failure instead.

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
    # Note that `just` and `sampled_from` count as "reusable" even if their
    # values are mutable, because the user has implicitly promised that they
    # don't care about the same mutable value being returned by separate draws.
    st.just([]),
    st.sampled_from([[]]),
    st.tuples(st.integers()),
)


@st.deferred
def reusable():
    """Meta-strategy that produces strategies that should have
    ``.has_reusable_values == True``."""
    return st.one_of(
        # This looks like it should be `one_of`, but `sampled_from` is correct
        # because we want this meta-strategy to yield strategies as its values.
        st.sampled_from(base_reusable_strategies),
        # This sometimes produces invalid combinations of arguments, which
        # we filter out further down with an explicit validation check.
        st.builds(
            st.floats,
            min_value=st.none() | st.floats(allow_nan=False),
            max_value=st.none() | st.floats(allow_nan=False),
            allow_infinity=st.booleans(),
            allow_nan=st.booleans(),
        ),
        st.builds(st.just, st.builds(list)),
        st.builds(st.sampled_from, st.lists(st.builds(list), min_size=1)),
        st.lists(reusable).map(st.one_of),
        st.lists(reusable).map(lambda ls: st.tuples(*ls)),
    )


def is_valid(s):
    try:
        s.validate()
        return True
    except InvalidArgument:
        return False


reusable = reusable.filter(is_valid)

assert not reusable.is_empty


def many_examples(examples):
    """Helper decorator to apply the ``@example`` decorator multiple times,
    once for each given example."""

    def accept(f):
        for e in examples:
            f = example(e)(f)
        return f

    return accept


@many_examples(base_reusable_strategies)
@many_examples(st.tuples(s) for s in base_reusable_strategies)
@given(reusable)
def test_reusable_strategies_are_all_reusable(s):
    assert s.has_reusable_values


@many_examples(base_reusable_strategies)
@given(reusable)
def test_filter_breaks_reusability(s):
    cond = True

    def nontrivial_filter(x):
        """Non-trivial filtering function, intended to remain opaque even if
        some strategies introspect their filters."""
        return cond

    assert s.has_reusable_values
    assert not s.filter(nontrivial_filter).has_reusable_values


@many_examples(base_reusable_strategies)
@given(reusable)
def test_map_breaks_reusability(s):
    cond = True

    def nontrivial_map(x):
        """Non-trivial mapping function, intended to remain opaque even if
        some strategies introspect their mappings."""
        if cond:
            return x
        else:
            return None

    assert s.has_reusable_values
    assert not s.map(nontrivial_map).has_reusable_values


@many_examples(base_reusable_strategies)
@given(reusable)
def test_flatmap_breaks_reusability(s):
    cond = True

    def nontrivial_flatmap(x):
        """Non-trivial flat-mapping function, intended to remain opaque even
        if some strategies introspect their flat-mappings."""
        if cond:
            return st.just(x)
        else:
            return st.none()

    assert s.has_reusable_values
    assert not s.flatmap(nontrivial_flatmap).has_reusable_values


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
