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
import functools
import itertools
import operator

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.internal.compat import bit_count
from hypothesis.strategies._internal.strategies import SampledFromStrategy

from tests.common.debug import find_any, minimal
from tests.common.utils import fails_with


@pytest.mark.parametrize("size", [100, 10**5, 10**6, 2**25])
@given(data=st.data())
def test_filter_large_lists(data, size):
    n_calls = 0

    def cond(x):
        nonlocal n_calls
        n_calls += 1
        return x % 2 != 0

    s = data.draw(st.sampled_from(range(size)).filter(cond))

    assert s % 2 != 0
    assert n_calls <= SampledFromStrategy._MAX_FILTER_CALLS


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
    c = enum.auto()


LargeFlag = enum.Flag("LargeFlag", {f"bit{i}": enum.auto() for i in range(64)})


class UnnamedFlag(enum.Flag):
    # Would fail under EnumCheck.NAMED_FLAGS
    a = 0
    b = 7


def test_flag_enum_repr_uses_class_not_a_list():
    lazy_repr = repr(st.sampled_from(AFlag))
    assert lazy_repr == "sampled_from(tests.nocover.test_sampled_from.AFlag)"


def test_exhaustive_flags():
    # Generate powerset of flag combinations. There are only 2^3 of them, so
    # we can reasonably expect that they are all are found.
    unseen_flags = {
        functools.reduce(operator.or_, flaglist, AFlag(0))
        for r in range(len(AFlag) + 1)
        for flaglist in itertools.combinations(AFlag, r)
    }

    @given(st.sampled_from(AFlag))
    def accept(flag):
        unseen_flags.discard(flag)

    accept()

    assert not unseen_flags


def test_flags_minimize_to_first_named_flag():
    assert minimal(st.sampled_from(LargeFlag)) == LargeFlag.bit0


def test_flags_minimizes_bit_count():
    assert (
        minimal(st.sampled_from(LargeFlag), lambda f: bit_count(f.value) > 1)
        == LargeFlag.bit0 | LargeFlag.bit1
    )


@pytest.mark.skipif(
    settings._current_profile == "crosshair",
    reason="takes ~10 mins; path tree is too large",
)
def test_flags_finds_all_bits_set():
    assert find_any(st.sampled_from(LargeFlag), lambda f: f == ~LargeFlag(0))


def test_sample_unnamed_alias():
    assert find_any(st.sampled_from(UnnamedFlag), lambda f: f == UnnamedFlag.b)


def test_shrink_to_named_empty():
    assert minimal(st.sampled_from(UnnamedFlag)) == UnnamedFlag(0)
