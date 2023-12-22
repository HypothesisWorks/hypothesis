# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import collections
import enum

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import (
    FailedHealthCheck,
    InvalidArgument,
    StopTest,
    Unsatisfiable,
)
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.strategies import sampled_from
from hypothesis.strategies._internal.misc import JustStrategy
from hypothesis.strategies._internal.strategies import (
    FilteredStrategy,
    filter_not_satisfied,
)

from tests.common.utils import fails_with

an_enum = enum.Enum("A", "a b c")

an_ordereddict = collections.OrderedDict([("a", 1), ("b", 2), ("c", 3)])


@fails_with(InvalidArgument)
def test_cannot_sample_sets():
    sampled_from(set("abc")).example()


def test_can_sample_sequence_without_warning():
    sampled_from([1, 2, 3]).example()


def test_can_sample_ordereddict_without_warning():
    sampled_from(an_ordereddict).example()


@given(sampled_from(an_enum))
def test_can_sample_enums(member):
    assert isinstance(member, an_enum)


@fails_with(FailedHealthCheck)
@given(sampled_from(range(10)).filter(lambda x: x < 0))
def test_unsat_filtered_sampling(x):
    raise AssertionError


@fails_with(Unsatisfiable)
@given(sampled_from(range(2)).filter(lambda x: x < 0))
def test_unsat_filtered_sampling_in_rejection_stage(x):
    # Rejecting all possible indices before we calculate the allowed indices
    # takes an early exit path, so we need this test to cover that branch.
    raise AssertionError


def test_easy_filtered_sampling():
    x = sampled_from(range(100)).filter(lambda x: x == 0).example()
    assert x == 0


@given(sampled_from(range(100)).filter(lambda x: x == 99))
def test_filtered_sampling_finds_rare_value(x):
    assert x == 99


@given(st.sets(st.sampled_from(range(50)), min_size=50))
def test_efficient_sets_of_samples(x):
    assert x == set(range(50))


@given(st.dictionaries(keys=st.sampled_from(range(50)), values=st.none(), min_size=50))
def test_efficient_dicts_with_sampled_keys(x):
    assert set(x) == set(range(50))


@given(
    st.lists(
        st.tuples(st.sampled_from(range(20)), st.builds(list)),
        min_size=20,
        unique_by=lambda asdf: asdf[0],
    )
)
def test_efficient_lists_of_tuples_first_element_sampled_from(x):
    assert {first for first, *_ in x} == set(range(20))


@given(st.lists(st.sampled_from([0] * 100), unique=True))
def test_does_not_include_duplicates_even_when_duplicated_in_collection(ls):
    assert len(ls) <= 1


@given(
    st.sets(
        st.sampled_from(range(50))
        .map(lambda x: x * 2)
        .filter(lambda x: x % 3)
        .map(lambda x: x // 2),
        min_size=33,
    )
)
def test_efficient_sets_of_samples_with_chained_transformations(x):
    assert x == {x for x in range(50) if (x * 2) % 3}


@st.composite
def stupid_sampled_sets(draw):
    result = set()
    s = st.sampled_from(range(20)).filter(lambda x: x % 3).map(lambda x: x * 2)
    while len(result) < 13:
        result.add(draw(s.filter(lambda x: x not in result)))
    return result


@given(stupid_sampled_sets())
def test_efficient_sets_of_samples_with_chained_transformations_slow_path(x):
    # This deliberately exercises the standard filtering logic without going
    # through the special-case handling of UniqueSampledListStrategy.
    assert x == {x * 2 for x in range(20) if x % 3}


@fails_with(Unsatisfiable)
@given(FilteredStrategy(st.sampled_from([None, False, ""]), conditions=(bool,)))
def test_unsatisfiable_explicit_filteredstrategy_sampled(x):
    raise AssertionError("Unreachable because there are no valid examples")


@fails_with(Unsatisfiable)
@given(FilteredStrategy(st.none(), conditions=(bool,)))
def test_unsatisfiable_explicit_filteredstrategy_just(x):
    raise AssertionError("Unreachable because there are no valid examples")


def test_transformed_just_strategy():
    data = ConjectureData.for_buffer(bytes(100))
    s = JustStrategy([1]).map(lambda x: x * 2)
    assert s.do_draw(data) == 2
    sf = s.filter(lambda x: False)
    assert isinstance(sf, JustStrategy)
    assert sf.do_filtered_draw(data) == filter_not_satisfied
    with pytest.raises(StopTest):
        sf.do_draw(data)


@given(st.lists(st.sampled_from(range(100)), max_size=3, unique=True))
def test_max_size_is_respected_with_unique_sampled_from(ls):
    assert len(ls) <= 3


@given(st.lists(st.sampled_from([0, 0.0]), unique=True, min_size=1))
def test_issue_2247_regression(ls):
    assert len(ls) == 1


@given(st.data())
def test_mutability_1(data):
    # See https://github.com/HypothesisWorks/hypothesis/issues/2507
    x = [1]
    s = st.sampled_from(x)
    x.append(2)
    assert data.draw(s) != 2


@given(st.data())
def test_mutability_2(data):
    x = [1]
    s = st.sampled_from(x)
    assert data.draw(s) != 2
    x.append(2)
    assert data.draw(s) != 2


class AnnotationsInsteadOfElements(enum.Enum):
    a: "int"


def test_suggests_elements_instead_of_annotations():
    with pytest.raises(InvalidArgument, match="Cannot sample.*annotations.*dataclass"):
        st.sampled_from(AnnotationsInsteadOfElements).example()


@pytest.mark.parametrize("wrap", [list, tuple])
def test_warns_when_given_entirely_strategies_as_elements(wrap):
    elements = wrap([st.booleans(), st.decimals(), st.integers(), st.text()])
    with pytest.warns(
        UserWarning,
        match="sample_from was given a collection of strategies; was one_of intended?",
    ):
        st.sampled_from(elements)
