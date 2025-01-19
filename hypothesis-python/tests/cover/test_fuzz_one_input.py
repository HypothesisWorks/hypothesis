# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import io
import unittest
from operator import attrgetter
from random import randbytes

import pytest

from hypothesis import Phase, given, settings, strategies as st
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.errors import InvalidArgument
from hypothesis.internal.conjecture.engine import shortlex


@pytest.mark.parametrize(
    "buffer_type",
    [bytes, bytearray, memoryview, io.BytesIO],
    ids=attrgetter("__name__"),
)
def test_fuzz_one_input(buffer_type):
    db = InMemoryExampleDatabase()
    seen = []
    seeds = []

    # This is a standard `@given` test, which we can also use as a fuzz target.
    # Note that we specify the DB so we can make more precise assertions,
    # and tighten the phases so we can be sure the failing examples come from fuzzing.
    @given(st.text())
    @settings(database=db, phases=[Phase.reuse, Phase.shrink])
    def test(s):
        seen.append(s)
        assert len(s) < 5, repr(s)

    # Before running fuzz_one_input, there's nothing in `db`, and so the test passes
    # (because example generation is disabled by the custom settings)
    with pytest.raises(unittest.SkipTest):  # because this generates no examples
        test()
    assert len(seen) == 0

    # If we run a lot of random bytestrings through fuzz_one_input, we'll eventually
    # find a failing example.
    with pytest.raises(AssertionError):
        for _ in range(1000):
            buf = randbytes(1000)
            seeds.append(buf)
            test.hypothesis.fuzz_one_input(buffer_type(buf))

    # fuzz_one_input returns False for invalid bytestrings, due to e.g. assume(False)
    assert len(seen) <= len(seeds)

    # `db` contains exactly one failing example, which is either the most
    # recent seed that we tried or the pruned-and-canonicalised form of it.
    (saved_examples,) = db.data.values()
    assert len(saved_examples) == 1
    assert shortlex(seeds[-1]) >= shortlex(next(iter(saved_examples)))

    # Now that we have a failure in `db`, re-running our test is sufficient to
    # reproduce it, *and shrink to a minimal example*.
    with pytest.raises(AssertionError):
        test()
    assert seen[-1] == "0" * 5


def test_can_fuzz_with_database_eq_None():
    # This test exists to cover the can't-record-failure branch.

    @given(st.none())
    @settings(database=None)
    def test(s):
        raise AssertionError

    with pytest.raises(AssertionError):
        test.hypothesis.fuzz_one_input(b"\x00\x00")


def test_fuzzing_unsatisfiable_test_always_returns_None():
    # There are no examples of `st.none().filter(bool)`, but while the Hypothesis
    # engine would give up, fuzz_one_input will just return None each time.

    @given(st.none().filter(bool))
    @settings(database=None)
    def test(s):
        raise AssertionError("Unreachable because there are no valid examples")

    for _ in range(100):
        buf = randbytes(3)
        ret = test.hypothesis.fuzz_one_input(buf)
        assert ret is None


def test_autopruning_of_returned_buffer():
    @given(st.binary(min_size=4, max_size=4))
    @settings(database=None)
    def test(s):
        pass

    # Unused portions of the input buffer are discarded from output.
    # (and canonicalised, but that's a no-op for fixed-length `binary()`)
    assert test.hypothesis.fuzz_one_input(b"deadbeef") == b"dead"


STRAT = st.builds(object)


@given(x=STRAT)
def addx(x, y):
    pass


@given(STRAT)
def addy(x, y):
    pass


def test_can_access_strategy_for_wrapped_test():
    assert addx.hypothesis._given_kwargs == {"x": STRAT}
    assert addy.hypothesis._given_kwargs == {"y": STRAT}


@pytest.mark.parametrize(
    "buffers,db_size",
    [
        ([b"aa", b"bb", b"cc", b"dd"], 1),  # ascending -> only saves first
        ([b"dd", b"cc", b"bb", b"aa"], 4),  # descending -> saves all
        ([b"cc", b"dd", b"aa", b"bb"], 2),  # sawtooth -> saves cc then aa
        ([b"aa", b"bb", b"cc", b"XX"], 2),  # two distinct errors -> saves both
    ],
)
def test_fuzz_one_input_does_not_add_redundant_entries_to_database(buffers, db_size):
    db = InMemoryExampleDatabase()
    seen = []

    @given(st.binary(min_size=2, max_size=2))
    @settings(database=db)
    def test(s):
        seen.append(s)
        assert s != b"XX"
        raise AssertionError

    for buf in buffers:
        with pytest.raises(AssertionError):
            test.hypothesis.fuzz_one_input(buf)

    (saved_examples,) = db.data.values()
    assert seen == buffers
    assert len(saved_examples) == db_size


def test_fuzzing_invalid_test_raises_error():
    # Invalid: @given with too many positional arguments
    @given(st.integers(), st.integers())
    def invalid_test(s):
        pass

    with pytest.raises(InvalidArgument, match="Too many positional arguments"):
        # access the property to check error happens during setup
        invalid_test.hypothesis.fuzz_one_input
