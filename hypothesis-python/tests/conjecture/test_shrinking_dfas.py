# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys
from contextlib import contextmanager
from itertools import islice

import pytest

from hypothesis import settings
from hypothesis.internal.conjecture.data import Status
from hypothesis.internal.conjecture.engine import ConjectureRunner
from hypothesis.internal.conjecture.shrinking import dfas

TEST_DFA_NAME = "test name"


@contextmanager
def preserving_dfas():
    assert TEST_DFA_NAME not in dfas.SHRINKING_DFAS
    for k in dfas.SHRINKING_DFAS:
        assert not k.startswith(TEST_DFA_NAME)
    original = dict(dfas.SHRINKING_DFAS)
    try:
        yield
    finally:
        dfas.SHRINKING_DFAS.clear()
        dfas.SHRINKING_DFAS.update(original)
        dfas.update_learned_dfas()
    assert TEST_DFA_NAME not in dfas.SHRINKING_DFAS
    assert TEST_DFA_NAME not in dfas.learned_dfa_file.read_text(encoding="utf-8")


def test_updating_the_file_makes_no_changes_normally():
    source1 = dfas.learned_dfa_file.read_text(encoding="utf-8")

    dfas.update_learned_dfas()

    source2 = dfas.learned_dfa_file.read_text(encoding="utf-8")

    assert source1 == source2


def test_updating_the_file_include_new_shrinkers():
    with preserving_dfas():
        source1 = dfas.learned_dfa_file.read_text(encoding="utf-8")

        dfas.SHRINKING_DFAS[TEST_DFA_NAME] = "hello"

        dfas.update_learned_dfas()

        source2 = dfas.learned_dfa_file.read_text(encoding="utf-8")

        assert source1 != source2
        assert repr(TEST_DFA_NAME) in source2

    assert TEST_DFA_NAME not in dfas.SHRINKING_DFAS

    assert "test name" not in dfas.learned_dfa_file.read_text(encoding="utf-8")


def called_by_shrinker():
    frame = sys._getframe(0)
    while frame:
        fname = frame.f_globals.get("__file__", "")
        if os.path.basename(fname) == "shrinker.py":
            return True
        frame = frame.f_back
    return False


def a_bad_test_function():
    """Return a test function that we definitely can't normalize
    because it cheats shamelessly and checks whether it's being
    called by the shrinker and refuses to declare any new results
    interesting."""
    cache = {0: False}

    def test_function(data):
        n = data.draw_integer(0, 2**64 - 1)
        if n < 1000:
            return

        try:
            interesting = cache[n]
        except KeyError:
            interesting = cache.setdefault(n, not called_by_shrinker())

        if interesting:
            data.mark_interesting()

    return test_function


def test_will_error_if_does_not_normalise_and_cannot_update():
    with pytest.raises(dfas.FailedToNormalise) as excinfo:
        dfas.normalize(
            "bad",
            a_bad_test_function(),
            required_successes=10,
            allowed_to_update=False,
        )

    assert "not allowed" in excinfo.value.args[0]


def test_will_error_if_takes_too_long_to_normalize():
    with preserving_dfas():
        with pytest.raises(dfas.FailedToNormalise) as excinfo:
            dfas.normalize(
                "bad",
                a_bad_test_function(),
                required_successes=1000,
                allowed_to_update=True,
                max_dfas=0,
            )

        assert "too hard" in excinfo.value.args[0]


def non_normalized_test_function(data):
    """This test function has two discrete regions that it
    is hard to move between. It's basically unreasonable for
    our shrinker to be able to transform from one to the other
    because of how different they are."""
    data.draw_integer(0, 2**8 - 1)
    if data.draw_boolean():
        n = data.draw_integer(0, 2**10 - 1)
        if 100 < n < 1000:
            data.draw_integer(0, 2**8 - 1)
            data.mark_interesting()
    else:
        n = data.draw_integer(0, 2**64 - 1)
        if n > 10000:
            data.draw_integer(0, 2**8 - 1)
            data.mark_interesting()


def test_can_learn_to_normalize_the_unnormalized():
    with preserving_dfas():
        prev = len(dfas.SHRINKING_DFAS)

        dfas.normalize(
            TEST_DFA_NAME, non_normalized_test_function, allowed_to_update=True
        )

        assert len(dfas.SHRINKING_DFAS) == prev + 1


def test_will_error_on_uninteresting_test():
    with pytest.raises(AssertionError):
        dfas.normalize(TEST_DFA_NAME, lambda data: data.draw_integer(0, 2**64 - 1))


def test_makes_no_changes_if_already_normalized():
    def test_function(data):
        if data.draw_integer(0, 2**16 - 1) >= 1000:
            data.mark_interesting()

    with preserving_dfas():
        before = dict(dfas.SHRINKING_DFAS)

        dfas.normalize(TEST_DFA_NAME, test_function, allowed_to_update=True)

        after = dict(dfas.SHRINKING_DFAS)

        assert after == before


def test_learns_to_bridge_only_two():
    def test_function(data):
        m = data.draw_integer(0, 2**8 - 1)
        n = data.draw_integer(0, 2**8 - 1)

        if (m, n) in ((10, 100), (2, 8)):
            data.mark_interesting()

    runner = ConjectureRunner(
        test_function, settings=settings(database=None), ignore_limits=True
    )

    dfa = dfas.learn_a_new_dfa(
        runner, [10, 100], [2, 8], lambda d: d.status == Status.INTERESTING
    )

    assert dfa.max_length(dfa.start) == 2

    assert list(map(list, dfa.all_matching_strings())) == [
        [2, 8],
        [10, 100],
    ]


def test_learns_to_bridge_only_two_with_overlap():
    u = [50, 0, 0, 0, 50]
    v = [50, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 50]

    def test_function(data):
        for i in range(len(u)):
            c = data.draw_integer(0, 2**8 - 1)
            if c != u[i]:
                if c != v[i]:
                    return
                break
        else:
            data.mark_interesting()
        for j in range(i + 1, len(v)):
            if data.draw_integer(0, 2**8 - 1) != v[j]:
                return

        data.mark_interesting()

    runner = ConjectureRunner(
        test_function, settings=settings(database=None), ignore_limits=True
    )

    dfa = dfas.learn_a_new_dfa(runner, u, v, lambda d: d.status == Status.INTERESTING)

    assert list(islice(dfa.all_matching_strings(), 3)) == [b"", bytes(len(v) - len(u))]


def test_learns_to_bridge_only_two_with_suffix():
    u = [7]
    v = [0] * 10 + [7]

    def test_function(data):
        n = data.draw_integer(0, 2**8 - 1)
        if n == 7:
            data.mark_interesting()
        elif n != 0:
            return
        for _ in range(9):
            if data.draw_integer(0, 2**8 - 1) != 0:
                return
        if data.draw_integer(0, 2**8 - 1) == 7:
            data.mark_interesting()

    runner = ConjectureRunner(
        test_function, settings=settings(database=None), ignore_limits=True
    )

    dfa = dfas.learn_a_new_dfa(runner, u, v, lambda d: d.status == Status.INTERESTING)

    assert list(islice(dfa.all_matching_strings(), 3)) == [b"", bytes(len(v) - len(u))]
