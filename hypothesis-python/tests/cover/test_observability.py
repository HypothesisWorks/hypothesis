# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import contextlib

import pytest

from hypothesis import (
    assume,
    event,
    example,
    given,
    seed,
    settings,
    strategies as st,
    target,
)
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.internal.observability import TESTCASE_CALLBACKS


@contextlib.contextmanager
def capture_observations():
    ls = []
    TESTCASE_CALLBACKS.append(ls.append)
    try:
        yield ls
    finally:
        TESTCASE_CALLBACKS.remove(ls.append)


@seed("deterministic so we don't miss some combination of features")
@example(a=0, x=4, data=None)
@settings(database=InMemoryExampleDatabase(), deadline=None)
@given(st.integers(), st.integers(), st.data())
def do_it_all(a, x, data):
    event(f"{x%2=}")
    target(x % 5, label="x%5")
    assume(a % 9)
    if data:
        data.draw(st.text("abcdef", min_size=a % 3), label="interactive")
    1 / ((x or 1) % 7)


def test_observability():
    with capture_observations() as ls:
        with pytest.raises(ZeroDivisionError):
            do_it_all()
        with pytest.raises(ZeroDivisionError):
            do_it_all()

    infos = [t for t in ls if t["type"] == "info"]
    assert len(infos) == 2
    assert {t["title"] for t in infos} == {"Hypothesis Statistics"}

    testcases = [t for t in ls if t["type"] == "test_case"]
    assert len(testcases) > 50
    assert {t["property"] for t in testcases} == {do_it_all.__name__}
    assert len({t["run_start"] for t in testcases}) == 2
    assert {t["status"] for t in testcases} == {"gave_up", "passed", "failed"}
    for t in testcases:
        if t["status"] != "gave_up":
            assert t["timing"]
            assert ("interactive" in t["arguments"]) == (
                "generate:interactive" in t["timing"]
            )


def test_assume_has_status_reason():
    @given(st.booleans())
    def f(b):
        assume(b)

    with capture_observations() as ls:
        f()

    gave_ups = [t for t in ls if t["type"] == "test_case" and t["status"] == "gave_up"]
    for gave_up in gave_ups:
        assert gave_up["status_reason"] == "failed to satisfy assume() in f"
