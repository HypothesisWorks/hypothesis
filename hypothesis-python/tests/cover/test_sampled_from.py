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
import sys

import pytest

from hypothesis import given, settings, strategies as st
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

from tests.common.debug import (
    assert_all_examples,
    assert_simple_property,
    check_can_generate_examples,
)
from tests.common.utils import fails_with

an_enum = enum.Enum("A", "a b c")
a_flag = enum.Flag("A", "a b c")
# named zero state is required for empty flags from around py3.11/3.12
an_empty_flag = enum.Flag("EmptyFlag", {"a": 0})

an_ordereddict = collections.OrderedDict([("a", 1), ("b", 2), ("c", 3)])


@fails_with(InvalidArgument)
def test_cannot_sample_sets():
    check_can_generate_examples(sampled_from(set("abc")))


def test_can_sample_sequence_without_warning():
    check_can_generate_examples(sampled_from([1, 2, 3]))


def test_can_sample_ordereddict_without_warning():
    check_can_generate_examples(sampled_from(an_ordereddict))


@pytest.mark.parametrize("enum_class", [an_enum, a_flag, an_empty_flag])
def test_can_sample_enums(enum_class):
    assert_all_examples(sampled_from(enum_class), lambda x: isinstance(x, enum_class))


@fails_with(FailedHealthCheck)
@settings(suppress_health_check=[])
@given(sampled_from(range(10)).filter(lambda x: x < 0))
def test_unsat_filtered_sampling(x):
    raise AssertionError


@fails_with(Unsatisfiable)
@settings(suppress_health_check=[])
@given(sampled_from(range(2)).filter(lambda x: x < 0))
def test_unsat_filtered_sampling_in_rejection_stage(x):
    # Rejecting all possible indices before we calculate the allowed indices
    # takes an early exit path, so we need this test to cover that branch.
    raise AssertionError


def test_easy_filtered_sampling():
    assert_simple_property(
        sampled_from(range(100)).filter(lambda x: x == 0), lambda x: x == 0
    )


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
    data = ConjectureData.for_choices([])
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


@pytest.mark.skipif(sys.version_info[:2] >= (3, 14), reason="FIXME-py314")
def test_suggests_elements_instead_of_annotations():
    with pytest.raises(InvalidArgument, match="Cannot sample.*annotations.*dataclass"):
        check_can_generate_examples(st.sampled_from(AnnotationsInsteadOfElements))


class TestErrorNoteBehavior3819:
    elements = (st.booleans(), st.decimals(), st.integers(), st.text())

    @staticmethod
    @given(st.data())
    def direct_without_error(data):
        data.draw(st.sampled_from((st.floats(), st.binary())))

    @staticmethod
    @given(st.data())
    def direct_with_non_type_error(data):
        data.draw(st.sampled_from(st.characters(), st.floats()))
        raise Exception("Contains SearchStrategy, but no note addition!")

    @staticmethod
    @given(st.data())
    def direct_with_type_error_without_substring(data):
        data.draw(st.sampled_from(st.booleans(), st.binary()))
        raise TypeError("Substring not in message!")

    @staticmethod
    @given(st.data())
    def direct_with_type_error_with_substring_but_not_all_strategies(data):
        data.draw(st.sampled_from(st.booleans(), False, True))
        raise TypeError("Contains SearchStrategy, but no note addition!")

    @staticmethod
    @given(st.data())
    def direct_all_strategies_with_type_error_with_substring(data):
        data.draw(st.sampled_from((st.dates(), st.datetimes())))
        raise TypeError("This message contains SearchStrategy as substring!")

    @staticmethod
    @given(st.lists(st.sampled_from(elements)))
    def indirect_without_error(_):
        return

    @staticmethod
    @given(st.lists(st.sampled_from(elements)))
    def indirect_with_non_type_error(_):
        raise Exception("Contains SearchStrategy, but no note addition!")

    @staticmethod
    @given(st.lists(st.sampled_from(elements)))
    def indirect_with_type_error_without_substring(_):
        raise TypeError("Substring not in message!")

    @staticmethod
    @given(st.lists(st.sampled_from((*elements, False, True))))
    def indirect_with_type_error_with_substring_but_not_all_strategies(_):
        raise TypeError("Contains SearchStrategy, but no note addition!")

    @staticmethod
    @given(st.lists(st.sampled_from(elements), min_size=1))
    def indirect_all_strategies_with_type_error_with_substring(objs):
        raise TypeError("Contains SearchStrategy in message, trigger note!")

    @pytest.mark.parametrize(
        ["func_to_call", "exp_err_cls", "should_exp_msg"],
        [
            pytest.param(f.__func__, err, msg_exp, id=f.__func__.__name__)
            for f, err, msg_exp in [
                (f, TypeError, True)
                for f in (
                    direct_all_strategies_with_type_error_with_substring,
                    indirect_all_strategies_with_type_error_with_substring,
                )
            ]
            + [
                (f, TypeError, False)
                for f in (
                    direct_with_type_error_without_substring,
                    direct_with_type_error_with_substring_but_not_all_strategies,
                    indirect_with_type_error_without_substring,
                    indirect_with_type_error_with_substring_but_not_all_strategies,
                )
            ]
            + [
                (f, Exception, False)
                for f in (
                    direct_with_non_type_error,
                    indirect_with_non_type_error,
                )
            ]
            + [
                (f, None, False)
                for f in (
                    direct_without_error,
                    indirect_without_error,
                )
            ]
        ],
    )
    def test_error_appropriate_error_note_3819(
        self, func_to_call, exp_err_cls, should_exp_msg
    ):
        if exp_err_cls is None:
            # Here we only care that no exception was raised, so nothing to assert.
            func_to_call()
        else:
            with pytest.raises(exp_err_cls) as err_ctx:
                func_to_call()
            notes = getattr(err_ctx.value, "__notes__", [])
            matching_messages = [
                n
                for n in notes
                if n.startswith("sample_from was given a collection of strategies")
                and n.endswith("Was one_of intended?")
            ]
            assert len(matching_messages) == (1 if should_exp_msg else 0)
