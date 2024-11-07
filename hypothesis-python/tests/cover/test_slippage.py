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

from hypothesis import Phase, assume, given, settings, strategies as st, target
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.errors import FlakyFailure
from hypothesis.internal.compat import ExceptionGroup
from hypothesis.internal.conjecture.engine import MIN_TEST_CALLS

from tests.common.utils import (
    assert_output_contains_failure,
    capture_out,
    non_covering_examples,
)


def capture_reports(test):
    with capture_out() as o, pytest.raises(ExceptionGroup) as err:
        test()

    return o.getvalue() + "\n\n".join(
        f"{e!r}\n" + "\n".join(getattr(e, "__notes__", []))
        for e in (err.value, *err.value.exceptions)
    )


def test_raises_multiple_failures_with_varying_type():
    target = None

    @settings(database=None, max_examples=100, report_multiple_bugs=True)
    @given(st.integers())
    def test(i):
        nonlocal target
        if abs(i) < 1000:
            return
        if target is None:
            # Ensure that we have some space to shrink into, so we can't
            # trigger an minimal example and mask the other exception type.
            assume(1003 < abs(i))
            target = i
        exc_class = TypeError if target == i else ValueError
        raise exc_class

    output = capture_reports(test)
    assert "TypeError" in output
    assert "ValueError" in output


def test_shows_target_scores_with_multiple_failures():
    @settings(derandomize=True, max_examples=10_000)
    @given(st.integers())
    def test(i):
        target(i)
        assert i > 0
        assert i < 0

    assert "Highest target score:" in capture_reports(test)


def test_raises_multiple_failures_when_position_varies():
    target = None

    @settings(max_examples=100, report_multiple_bugs=True)
    @given(st.integers())
    def test(i):
        nonlocal target
        if abs(i) < 1000:
            return
        if target is None:
            target = i
        if target == i:
            raise ValueError("loc 1")
        else:
            raise ValueError("loc 2")

    output = capture_reports(test)
    assert "loc 1" in output
    assert "loc 2" in output


def test_replays_both_failing_values():
    target = None

    @settings(
        database=InMemoryExampleDatabase(), max_examples=500, report_multiple_bugs=True
    )
    @given(st.integers())
    def test(i):
        nonlocal target
        if abs(i) < 1000:
            return
        if target is None:
            target = i
        exc_class = TypeError if target == i else ValueError
        raise exc_class

    with pytest.raises(ExceptionGroup):
        test()

    with pytest.raises(ExceptionGroup):
        test()


@pytest.mark.parametrize("fix", [TypeError, ValueError])
def test_replays_slipped_examples_once_initial_bug_is_fixed(fix):
    target = []
    bug_fixed = False

    @settings(
        database=InMemoryExampleDatabase(), max_examples=500, report_multiple_bugs=True
    )
    @given(st.integers())
    def test(i):
        if abs(i) < 1000:
            return
        if not target:
            target.append(i)
        if i == target[0]:
            if bug_fixed and fix == TypeError:
                return
            raise TypeError
        if len(target) == 1:
            target.append(i)
        if bug_fixed and fix == ValueError:
            return
        if i == target[1]:
            raise ValueError

    with pytest.raises(ExceptionGroup):
        test()

    bug_fixed = True

    with pytest.raises(ValueError if fix == TypeError else TypeError):
        test()


def test_garbage_collects_the_secondary_key():
    target = []
    bug_fixed = False

    db = InMemoryExampleDatabase()

    @settings(database=db, max_examples=500, report_multiple_bugs=True)
    @given(st.integers())
    def test(i):
        if bug_fixed:
            return
        if abs(i) < 1000:
            return
        if not target:
            target.append(i)
        if i == target[0]:
            raise TypeError
        if len(target) == 1:
            target.append(i)
        if i == target[1]:
            raise ValueError

    with pytest.raises(ExceptionGroup):
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
    first_has_failed = False
    duds = set()
    second_target = None

    @settings(database=None, max_examples=1000, report_multiple_bugs=True)
    @given(st.integers(min_value=0))
    def test(i):
        nonlocal first_has_failed, duds, second_target

        if i >= 10000:
            first_has_failed = True
            raise AssertionError

        assert i < 10000
        if first_has_failed:
            if second_target is None:
                for j in range(10000):
                    if j not in duds:
                        second_target = j
                        break
            # to avoid flaky errors, don't error on an input that we previously
            # passed.
            if i not in duds:
                assert i < second_target
        else:
            duds.add(i)

    output = capture_reports(test)
    assert_output_contains_failure(output, test, i=10000)
    assert_output_contains_failure(output, test, i=second_target)


def test_handles_flaky_tests_where_only_one_is_flaky():
    flaky_fixed = False

    target = []
    flaky_failed_once = False

    @settings(
        database=InMemoryExampleDatabase(), max_examples=1000, report_multiple_bugs=True
    )
    @given(st.integers())
    def test(i):
        nonlocal flaky_failed_once
        if abs(i) < 1000:
            return
        if not target:
            target.append(i)
        if i == target[0]:
            raise TypeError
        if flaky_failed_once and not flaky_fixed:
            return
        if len(target) == 1:
            target.append(i)
        if i == target[1]:
            flaky_failed_once = True
            raise ValueError

    with pytest.raises(ExceptionGroup) as err:
        test()
    assert any(isinstance(e, FlakyFailure) for e in err.value.exceptions)

    flaky_fixed = True

    with pytest.raises(ExceptionGroup) as err:
        test()
    assert not any(isinstance(e, FlakyFailure) for e in err.value.exceptions)


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

    with pytest.raises(ExceptionGroup if allow_multi else TypeError):
        test()
    assert seen == {TypeError, ValueError}


def test_finds_multiple_failures_in_generation():
    special = None
    seen = set()

    @settings(
        phases=[Phase.generate, Phase.shrink],
        max_examples=100,
        report_multiple_bugs=True,
    )
    @given(st.integers(min_value=0))
    def test(x):
        """Constructs a test so the 10th largeish example we've seen is a
        special failure, and anything new we see after that point that
        is larger than it is a different failure. This demonstrates that we
        can keep generating larger examples and still find new bugs after that
        point."""
        nonlocal special
        if not special:
            # don't mark duplicate inputs as special and thus erroring, to avoid
            # flakiness where we passed the input the first time but failed it the
            # second.
            if len(seen) >= 10 and x <= 1000 and x not in seen:
                special = x
            else:
                seen.add(x)

        if special:
            assert x in seen or x <= special
        assert x != special

    with pytest.raises(ExceptionGroup):
        test()


def test_stops_immediately_if_not_report_multiple_bugs():
    seen = set()

    @settings(phases=[Phase.generate], report_multiple_bugs=False)
    @given(st.integers())
    def test(x):
        seen.add(x)
        raise AssertionError

    with pytest.raises(AssertionError):
        test()
    assert len(seen) == 1


def test_stops_immediately_on_replay():
    seen = set()

    @settings(database=InMemoryExampleDatabase(), phases=tuple(Phase)[:-1])
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
