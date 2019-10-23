# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
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

from __future__ import absolute_import, division, print_function

import pytest

import hypothesis.strategies as st
from hypothesis import Phase, assume, given, settings
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.errors import Flaky, MultipleFailures
from hypothesis.internal.conjecture.engine import MIN_TEST_CALLS
from tests.common.utils import capture_out, non_covering_examples


def test_raises_multiple_failures_with_varying_type():
    target = [None]

    @settings(database=None)
    @given(st.integers())
    def test(i):
        if abs(i) < 1000:
            return
        if target[0] is None:
            # Ensure that we have some space to shrink into, so we can't
            # trigger an minimal example and mask the other exception type.
            assume(1003 < abs(i))
            target[0] = i
        exc_class = TypeError if target[0] == i else ValueError
        raise exc_class()

    with capture_out() as o:
        with pytest.raises(MultipleFailures):
            test()

    assert "TypeError" in o.getvalue()
    assert "ValueError" in o.getvalue()


def test_raises_multiple_failures_when_position_varies():
    target = [None]

    @given(st.integers())
    def test(i):
        if abs(i) < 1000:
            return
        if target[0] is None:
            target[0] = i
        if target[0] == i:
            raise ValueError("loc 1")
        else:
            raise ValueError("loc 2")

    with capture_out() as o:
        with pytest.raises(MultipleFailures):
            test()
    assert "loc 1" in o.getvalue()
    assert "loc 2" in o.getvalue()


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


@pytest.mark.parametrize("fix", [TypeError, ValueError])
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

    @settings(database=None, max_examples=1000)
    @given(st.integers(min_value=0).map(int))
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

    assert "test(i=10000)" in o.getvalue()
    assert "test(i=%d)" % (second_target[0],) in o.getvalue()


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


@pytest.mark.parametrize("allow_multi", [True, False])
def test_can_disable_multiple_error_reporting(allow_multi):
    seen = set()

    @settings(database=None, derandomize=True, report_multiple_bugs=allow_multi)
    @given(st.integers(min_value=0))
    def test(i):
        # We will pass on the minimal i=0, then fail with a large i, and eventually
        # slip to i=1 and a different error.  We check both seen and raised errors.
        if i == 1:
            seen.add(TypeError)
            raise TypeError
        elif i >= 2:
            seen.add(ValueError)
            raise ValueError

    with pytest.raises(MultipleFailures if allow_multi else TypeError):
        test()
    assert seen == {TypeError, ValueError}


def test_finds_multiple_failures_in_generation():
    special = []
    seen = set()

    @settings(phases=[Phase.generate], max_examples=100)
    @given(st.integers(min_value=0))
    def test(x):
        """Constructs a test so the 10th largeish example we've seen is a
        special failure, and anything new we see after that point that
        is larger than it is a different failure. This demonstrates that we
        can keep generating larger examples and still find new bugs after that
        point."""
        if not special:
            if len(seen) >= 10 and x <= 1000:
                special.append(x)
            else:
                seen.add(x)
        if special:
            assert x in seen or (x <= special[0])
        assert x not in special

    with pytest.raises(MultipleFailures):
        test()


def test_stops_immediately_if_not_report_multiple_bugs():
    seen = set()

    @settings(phases=[Phase.generate], report_multiple_bugs=False)
    @given(st.integers())
    def test(x):
        seen.add(x)
        assert False

    with pytest.raises(AssertionError):
        test()
    assert len(seen) == 1


def test_stops_immediately_on_replay():
    seen = set()

    @settings(database=InMemoryExampleDatabase())
    @given(st.integers())
    def test(x):
        seen.add(x)
        assert x

    # On the first run, we look for up to ten examples:
    with pytest.raises(AssertionError):
        test()
    assert 1 < len(seen) <= MIN_TEST_CALLS

    # With failing examples in the database, we stop at one.
    seen.clear()
    with pytest.raises(AssertionError):
        test()
    assert len(seen) == 1
