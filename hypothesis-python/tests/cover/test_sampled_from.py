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

import collections
import enum

from hypothesis import given, strategies as st
from hypothesis.errors import FailedHealthCheck, InvalidArgument, Unsatisfiable
from hypothesis.strategies import sampled_from
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
    assert False


@fails_with(Unsatisfiable)
@given(sampled_from(range(2)).filter(lambda x: x < 0))
def test_unsat_filtered_sampling_in_rejection_stage(x):
    # Rejecting all possible indices before we calculate the allowed indices
    # takes an early exit path, so we need this test to cover that branch.
    assert False


def test_easy_filtered_sampling():
    x = sampled_from(range(100)).filter(lambda x: x == 0).example()
    assert x == 0


@given(sampled_from(range(100)).filter(lambda x: x == 99))
def test_filtered_sampling_finds_rare_value(x):
    assert x == 99


@given(st.sets(st.sampled_from(range(50)), min_size=50))
def test_efficient_sets_of_samples(x):
    assert x == set(range(50))


@given(st.lists(st.sampled_from([0] * 100), unique=True))
def test_does_not_include_duplicates_even_when_duplicated_in_collection(ls):
    assert len(ls) <= 1


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
