# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import hypothesis.strategies as st
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.strategies._internal.strategies import FilteredStrategy


def test_filter_iterations_are_marked_as_discarded():
    variable_equal_to_zero = 0  # non-local references disables filter-rewriting
    x = st.integers().filter(lambda x: x == variable_equal_to_zero)

    data = ConjectureData.for_choices([1, 0])
    assert data.draw(x) == 0
    assert data.has_discards


def test_filtered_branches_are_all_filtered():
    s = FilteredStrategy(st.integers() | st.text(), (bool,))
    assert all(isinstance(x, FilteredStrategy) for x in s.branches)


def test_filter_conditions_may_be_empty():
    s = FilteredStrategy(st.integers(), conditions=())
    s.condition(0)


def test_nested_filteredstrategy_flattens_conditions():
    s = FilteredStrategy(
        FilteredStrategy(st.text(), conditions=(bool,)),
        conditions=(len,),
    )
    assert s.filtered_strategy is st.text()
    assert s.flat_conditions == (bool, len)
