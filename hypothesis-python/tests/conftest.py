# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import gc
import random
import sys
import time as time_module

import pytest

from hypothesis._settings import is_in_ci
from hypothesis.internal.detection import is_hypothesis_test

from tests.common import TIME_INCREMENT
from tests.common.setup import run

run()

# Skip collection of tests which require the Django test runner,
# or that don't work on the current version of Python.
collect_ignore_glob = ["django/*"]
if sys.version_info < (3, 8):
    collect_ignore_glob.append("array_api")
    collect_ignore_glob.append("cover/*py38*")
if sys.version_info < (3, 9):
    collect_ignore_glob.append("cover/*py39*")
if sys.version_info < (3, 10):
    collect_ignore_glob.append("cover/*py310*")

if sys.version_info >= (3, 11):
    collect_ignore_glob.append("cover/test_asyncio.py")  # @asyncio.coroutine removed


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: pandas expects this marker to exist.")


def pytest_addoption(parser):
    parser.addoption("--hypothesis-update-outputs", action="store_true")
    parser.addoption("--hypothesis-learn-to-normalize", action="store_true")


@pytest.fixture(scope="function", autouse=True)
def gc_before_each_test():
    gc.collect()


@pytest.fixture(scope="function", autouse=True)
def consistently_increment_time(monkeypatch):
    """Rather than rely on real system time we monkey patch time.time so that
    it passes at a consistent rate between calls.

    The reason for this is that when these tests run in CI, their performance is
    extremely variable and the VM the tests are on might go to sleep for a bit,
    introducing arbitrary delays. This can cause a number of tests to fail
    flakily.

    Replacing time with a fake version under our control avoids this problem.
    """
    frozen = [False]

    current_time = [time_module.time()]

    def time():
        if not frozen[0]:
            current_time[0] += TIME_INCREMENT
        return current_time[0]

    def sleep(naptime):
        current_time[0] += naptime

    def freeze():
        frozen[0] = True

    monkeypatch.setattr(time_module, "time", time)
    monkeypatch.setattr(time_module, "monotonic", time)
    monkeypatch.setattr(time_module, "perf_counter", time)
    monkeypatch.setattr(time_module, "sleep", sleep)
    monkeypatch.setattr(time_module, "freeze", freeze, raising=False)


random_states_after_tests = {}
independent_random = random.Random()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    # This hookwrapper checks for PRNG state leaks from Hypothesis tests.
    # See: https://github.com/HypothesisWorks/hypothesis/issues/1919
    if not (hasattr(item, "obj") and is_hypothesis_test(item.obj)):
        yield
    elif "pytest_randomly" in sys.modules:
        # See https://github.com/HypothesisWorks/hypothesis/issues/3041 - this
        # branch exists to make it easier on external contributors, but should
        # never run in our CI (because that would disable the check entirely).
        assert not is_in_ci()
        yield
    else:
        # We start by peturbing the state of the PRNG, because repeatedly
        # leaking PRNG state resets state_after to the (previously leaked)
        # state_before, and that just shows as "no use of random".
        random.seed(independent_random.randrange(2**32))
        before = random.getstate()
        yield
        after = random.getstate()
        if before != after:
            if after in random_states_after_tests:
                raise Exception(
                    f"{item.nodeid!r} and {random_states_after_tests[after]!r} "
                    "both used the `random` module, and finished with the "
                    "same global `random.getstate()`; this is probably a nasty bug!"
                )
            random_states_after_tests[after] = item.nodeid
