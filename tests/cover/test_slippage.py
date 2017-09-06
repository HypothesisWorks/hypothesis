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
from hypothesis.database import InMemoryExampleDatabase


def test_does_not_slip_into_other_exception_type():
    target = [None]

    @given(st.integers())
    def test(i):
        if abs(i) < 1000:
            return
        if target[0] is None:
            target[0] = i
        exc_class = TypeError if target[0] == i else ValueError
        raise exc_class()

    with pytest.raises(TypeError):
        test()


def test_does_not_slip_into_other_exception_location():
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

    with pytest.raises(ValueError) as e:
        test()
    assert e.value.args[0] == 'loc 1'


def test_does_not_slip_on_replay():
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

    with pytest.raises(TypeError):
        test()

    with pytest.raises(TypeError):
        test()


def test_replays_slipped_examples_once_initial_bug_is_fixed():
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
            if bug_fixed:
                return
            raise TypeError()
        if len(target) == 1:
            target.append(i)
        if i == target[1]:
            raise ValueError()

    with pytest.raises(TypeError):
        test()

    bug_fixed = True

    with pytest.raises(ValueError):
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

    with pytest.raises(TypeError):
        test()

    bug_fixed = True

    def count():
        return sum(len(v) for v in db.data.values())

    prev = count()
    while prev > 0:
        test()
        current = count()
        assert current < prev
        prev = current
