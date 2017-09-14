# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import pytest

import hypothesis.strategies as st
from hypothesis import given, settings
from hypothesis.errors import Flaky, MultipleFailures
from tests.common.utils import capture_out, non_covering_examples
from hypothesis.database import InMemoryExampleDatabase


def test_raises_multiple_failures_with_varying_type():
    target = [None]

    @given(st.integers())
    def test(i):
        if abs(i) < 1000:
            return
        if target[0] is None:
            target[0] = i
        exc_class = TypeError if target[0] == i else ValueError
        raise exc_class()

    with capture_out() as o:
        with pytest.raises(MultipleFailures):
            test()

    assert 'TypeError' in o.getvalue()
    assert 'ValueError' in o.getvalue()


def test_raises_multiple_failures_when_position_varies():
    target = [None]

    @given(st.integers())
    def test(i):
        if abs(i) < 1000:
            return
        if target[0] is None:
            target[0] = i
        if target[0] == i:
            raise ValueError('loc 1')
        else:
            raise ValueError('loc 2')

    with capture_out() as o:
        with pytest.raises(MultipleFailures):
            test()
    assert 'loc 1' in o.getvalue()
    assert 'loc 2' in o.getvalue()


def test_replays_both_failing_values():
    target = [None]

    @settings(database=InMemoryExampleDatabase())
    @given(st.integers())
    def test(i):
        if abs(i) < 1000:
            return
        if target[0] is None:
            target[0] = i
        exc_class = TypeError if target[0] == i else ValueError
        raise exc_class()

    with pytest.raises(MultipleFailures):
        test()

    with pytest.raises(MultipleFailures):
        test()


@pytest.mark.parametrize('fix', [TypeError, ValueError])
def test_replays_slipped_examples_once_initial_bug_is_fixed(fix):
    target = []
    bug_fixed = False

    @settings(database=InMemoryExampleDatabase())
    @given(st.integers())
    def test(i):
        if abs(i) < 1000:
            return
        if not target:
            target.append(i)
        if i == target[0]:
            if bug_fixed and fix == TypeError:
                return
            raise TypeError()
        if len(target) == 1:
            target.append(i)
        if bug_fixed and fix == ValueError:
            return
        if i == target[1]:
            raise ValueError()

    with pytest.raises(MultipleFailures):
        test()

    bug_fixed = True

    with pytest.raises(ValueError if fix == TypeError else TypeError):
        test()


def test_garbage_collects_the_secondary_key():
    target = []
    bug_fixed = False

    db = InMemoryExampleDatabase()

    @settings(database=db)
    @given(st.integers())
    def test(i):
        if bug_fixed:
            return
        if abs(i) < 1000:
            return
        if not target:
            target.append(i)
        if i == target[0]:
            raise TypeError()
        if len(target) == 1:
            target.append(i)
        if i == target[1]:
            raise ValueError()

    with pytest.raises(MultipleFailures):
        test()

    bug_fixed = True

    def count():
        return len(non_covering_examples(db))

    prev = count()
    while prev > 0:
        test()
        current = count()
        assert current < prev
        prev = current


def test_shrinks_both_failures():
    first_has_failed = [False]
    duds = set()
    second_target = [None]

    @given(st.integers())
    def test(i):
        if i >= 10000:
            first_has_failed[0] = True
            assert False
        assert i < 10000
        if first_has_failed[0]:
            if second_target[0] is None:
                for j in range(10000):
                    if j not in duds:
                        second_target[0] = j
                        break
            assert i < second_target[0]
        else:
            duds.add(i)

    with capture_out() as o:
        with pytest.raises(MultipleFailures):
            test()

    assert 'test(i=10000)' in o.getvalue()
    assert 'test(i=%d)' % (second_target[0],) in o.getvalue()


def test_handles_flaky_tests_where_only_one_is_flaky():
    flaky_fixed = False

    target = []
    flaky_failed_once = [False]

    @settings(database=InMemoryExampleDatabase())
    @given(st.integers())
    def test(i):
        if abs(i) < 1000:
            return
        if not target:
            target.append(i)
        if i == target[0]:
            raise TypeError()
        if flaky_failed_once[0] and not flaky_fixed:
            return
        if len(target) == 1:
            target.append(i)
        if i == target[1]:
            flaky_failed_once[0] = True
            raise ValueError()

    with pytest.raises(Flaky):
        test()

    flaky_fixed = True

    with pytest.raises(MultipleFailures):
        test()
