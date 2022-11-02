# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import enum

import pytest

from tests.common.utils import counts_calls, fails_with

from hypothesis import given, strategies as st
from hypothesis.errors import InvalidArgument

@pytest.mark.parametrize("n", [100, 10**5, 10**6, 2**25])
def test_filter_large_lists(n):
    filter_limit = 100 * 10000

    @counts_calls
    def cond(x):
        assert cond.calls < filter_limit
        return x % 2 != 0

    s = st.sampled_from(range(n)).filter(cond)

    @given(s)
    def run(x):
        assert x % 2 != 0

    run()

    assert cond.calls < filter_limit


def rare_value_strategy(n, target):
    def forbid(s, forbidden):
        """Helper function to avoid Python variable scoping issues."""
        return s.filter(lambda x: x != forbidden)

    s = st.sampled_from(range(n))
    for i in range(n):
        if i != target:
            s = forbid(s, i)

    return s


@given(rare_value_strategy(n=128, target=80))
def test_chained_filters_find_rare_value(x):
    assert x == 80


@fails_with(InvalidArgument)
@given(st.sets(st.sampled_from(range(10)), min_size=11))
def test_unsat_sets_of_samples(x):
    raise AssertionError


@given(st.sets(st.sampled_from(range(50)), min_size=50))
def test_efficient_sets_of_samples(x):
    assert x == set(range(50))


class AnEnum(enum.Enum):
    a = enum.auto()
    b = enum.auto()


def test_enum_repr_uses_class_not_a_list():
    # The repr should have enough detail to find the class again
    # (which is very useful for the ghostwriter logic we're working on)
    lazy_repr = repr(st.sampled_from(AnEnum))
    assert lazy_repr == "sampled_from(tests.nocover.test_sampled_from.AnEnum)"


class AFlag(enum.Flag):
    a = enum.auto()
    b = enum.auto()


def test_flag_enum_repr_uses_class_not_a_list():
    lazy_repr = repr(st.sampled_from(AFlag))
    assert lazy_repr == "sampled_from(tests.nocover.test_sampled_from.AFlag)"
