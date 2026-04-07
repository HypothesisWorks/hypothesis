# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import unittest

import pytest
from _pytest.outcomes import Failed, Skipped

from hypothesis import Phase, example, find, given, reject, settings, strategies as st
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.errors import InvalidArgument, NoSuchExample, Unsatisfiable


def test_stops_after_max_examples_if_satisfying():
    count = 0

    def track(x):
        nonlocal count
        count += 1
        return False

    max_examples = 100

    with pytest.raises(NoSuchExample):
        find(st.integers(0, 10000), track, settings=settings(max_examples=max_examples))

    assert count == max_examples


def test_stops_after_ten_times_max_examples_if_not_satisfying():
    count = 0

    def track(x):
        nonlocal count
        count += 1
        reject()

    max_examples = 100
    with pytest.raises(Unsatisfiable):
        find(st.integers(0, 10000), track, settings=settings(max_examples=max_examples))

    # Very occasionally we can generate overflows in generation, which also
    # count towards our example budget, which means that we don't hit the
    # maximum.
    assert count <= 10 * max_examples


some_normal_settings = settings()


def test_is_not_normally_default():
    assert settings.default is not some_normal_settings


@given(st.booleans())
@some_normal_settings
def test_settings_are_default_in_given(x):
    assert settings.default is some_normal_settings


def test_given_shrinks_pytest_helper_errors():
    final_value = None

    @settings(derandomize=True, max_examples=100)
    @given(st.integers())
    def inner(x):
        nonlocal final_value
        final_value = x
        if x > 100:
            pytest.fail(f"{x=} is too big!")

    with pytest.raises(Failed):
        inner()
    assert final_value == 101


def test_pytest_skip_skips_shrinking():
    seen_large = False

    @settings(derandomize=True, max_examples=100)
    @given(st.integers())
    def inner(x):
        nonlocal seen_large
        if x > 100:
            if seen_large:
                raise Exception("Should never replay a skipped test!")
            seen_large = True
            pytest.skip(f"{x=} is too big!")

    with pytest.raises(Skipped):
        inner()


def test_can_find_with_db_eq_none():
    find(st.integers(), bool, settings=settings(database=None, max_examples=100))


def test_no_such_example():
    with pytest.raises(NoSuchExample):
        find(st.none(), bool, database_key=b"no such example")


def test_validates_strategies_for_test_method():
    invalid_strategy = st.lists(st.nothing(), min_size=1)

    class TestStrategyValidation:
        @given(invalid_strategy)
        def test_method_with_bad_strategy(self, x):
            pass

    instance = TestStrategyValidation()
    with pytest.raises(InvalidArgument):
        instance.test_method_with_bad_strategy()


@example(1)
@given(st.integers())
@settings(phases=[Phase.target, Phase.shrink, Phase.explain])
def no_phases(_):
    raise Exception


@given(st.integers())
@settings(phases=[Phase.explicit])
def no_explicit(_):
    raise Exception


@given(st.integers())
@settings(phases=[Phase.reuse], database=InMemoryExampleDatabase())
def empty_db(_):
    raise Exception


@pytest.mark.parametrize(
    "test_fn",
    [no_phases, no_explicit, empty_db],
    ids=lambda t: t.__name__,
)
def test_non_executed_tests_raise_skipped(test_fn):
    with pytest.raises(unittest.SkipTest):
        test_fn()


@pytest.mark.parametrize(
    "codec, max_codepoint, exclude_categories, categories",
    [
        ("ascii", None, None, None),
        ("ascii", 128, None, None),
        ("ascii", 100, None, None),
        ("utf-8", None, None, None),
        ("utf-8", None, ["Cs"], None),
        ("utf-8", None, ["N"], None),
        ("utf-8", None, None, ["N"]),
    ],
)
@given(st.data())
def test_characters_codec(codec, max_codepoint, exclude_categories, categories, data):
    strategy = st.characters(
        codec=codec,
        max_codepoint=max_codepoint,
        exclude_categories=exclude_categories,
        categories=categories,
    )
    example = data.draw(strategy)
    assert example.encode(encoding=codec).decode(encoding=codec) == example
