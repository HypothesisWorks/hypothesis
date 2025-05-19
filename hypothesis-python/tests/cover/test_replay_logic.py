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

from hypothesis import given, settings, strategies as st
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.internal.compat import ExceptionGroup


def test_does_not_shrink_on_replay():
    database = InMemoryExampleDatabase()

    call_count = 0

    is_first = True
    last = None

    @settings(
        database=database,
        report_multiple_bugs=False,
        derandomize=False,
        max_examples=1000,
    )
    @given(st.lists(st.integers(), unique=True, min_size=3))
    def test(ls):
        nonlocal call_count, is_first, last
        if is_first and last is not None:
            assert ls == last
        is_first = False
        last = ls
        call_count += 1
        raise AssertionError

    with pytest.raises(AssertionError):
        test()

    assert last is not None

    call_count = 0
    is_first = True

    with pytest.raises(AssertionError):
        test()

    assert call_count == 2


def test_does_not_shrink_on_replay_with_multiple_bugs():
    database = InMemoryExampleDatabase()

    call_count = 0

    tombstone = 1000093

    @settings(
        database=database,
        report_multiple_bugs=True,
        derandomize=False,
        max_examples=1000,
    )
    @given(st.integers())
    def test(i):
        nonlocal call_count
        call_count += 1
        if i > tombstone:
            raise AssertionError
        elif i == tombstone:
            raise AssertionError

    with pytest.raises(ExceptionGroup):
        test()

    call_count = 0

    with pytest.raises(ExceptionGroup):
        test()

    assert call_count == 4


def test_will_always_shrink_if_previous_example_does_not_replay():
    database = InMemoryExampleDatabase()

    good = set()
    last = None

    @settings(
        database=database,
        report_multiple_bugs=True,
        derandomize=False,
        max_examples=1000,
    )
    @given(st.integers(min_value=0))
    def test(i):
        nonlocal last
        if i not in good:
            last = i
            raise AssertionError

    for i in range(20):
        with pytest.raises(AssertionError):
            test()
        assert last == i
        good.add(last)


def test_will_shrink_if_the_previous_example_does_not_look_right():
    database = InMemoryExampleDatabase()

    last = None

    first_test = True

    @settings(database=database, report_multiple_bugs=True, derandomize=False)
    @given(st.data())
    def test(data):
        nonlocal last
        m = data.draw(st.integers())
        last = m
        if first_test:
            data.draw(st.integers())
            assert m < 10000
        else:
            raise AssertionError

    with pytest.raises(AssertionError):
        test()

    assert last is not None
    assert last > 0

    first_test = False

    with pytest.raises(AssertionError):
        test()

    assert last == 0
