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
from functools import wraps

import pytest

from hypothesis._settings import is_in_ci
from hypothesis.errors import NonInteractiveExampleWarning
from hypothesis.internal.compat import add_note
from hypothesis.internal.conjecture import junkdrawer
from hypothesis.internal.detection import is_hypothesis_test

from tests.common import TIME_INCREMENT
from tests.common.setup import run

run()

# Skip collection of tests which require the Django test runner,
# or that don't work on the current version of Python.
collect_ignore_glob = ["django/*"]
if sys.version_info < (3, 9):
    collect_ignore_glob.append("cover/*py39*")
    collect_ignore_glob.append("patching/*")
if sys.version_info < (3, 10):
    collect_ignore_glob.append("cover/*py310*")

if sys.version_info >= (3, 11):
    collect_ignore_glob.append("cover/test_asyncio.py")  # @asyncio.coroutine removed


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: pandas expects this marker to exist.")
    config.addinivalue_line(
        "markers",
        "xp_min_version(api_version): run when greater or equal to api_version",
    )


def pytest_addoption(parser):
    parser.addoption("--hypothesis-update-outputs", action="store_true")
    parser.addoption("--hypothesis-learn-to-normalize", action="store_true")

    # New in pytest 6, so we add a shim on old versions to avoid missing-arg errors
    arg = "--durations-min"
    if arg not in sum((a._long_opts for g in parser._groups for a in g.options), []):
        parser.addoption(arg, action="store", default=1.0)


@pytest.fixture(scope="function", autouse=True)
def _gc_before_each_test():
    gc.collect()


@pytest.fixture(scope="function", autouse=True)
def _consistently_increment_time(monkeypatch):
    """Rather than rely on real system time we monkey patch time.time so that
    it passes at a consistent rate between calls.

    The reason for this is that when these tests run in CI, their performance is
    extremely variable and the VM the tests are on might go to sleep for a bit,
    introducing arbitrary delays. This can cause a number of tests to fail
    flakily.

    Replacing time with a fake version under our control avoids this problem.
    """
    frozen = {0: False}  # dict to make it a valid monkeypatch target

    current_time = [time_module.time()]

    def time():
        if not frozen[0]:
            current_time[0] += TIME_INCREMENT
        return current_time[0]

    def sleep(naptime):
        current_time[0] += naptime

    def freeze():
        frozen[0] = True

    def _patch(name, fn):
        monkeypatch.setattr(time_module, name, wraps(getattr(time_module, name))(fn))

    _patch("time", time)
    _patch("monotonic", time)
    _patch("perf_counter", time)
    _patch("sleep", sleep)
    monkeypatch.setattr(time_module, "freeze", freeze, raising=False)

    # In the patched time regime, observing it causes it to increment. To avoid reintroducing
    # non-determinism due to GC running at arbitrary times, we patch the GC observer
    # to NOT increment time. NOTE: This is not necessary, and has no effect, outside of CPython.

    orig_callback = junkdrawer._gc_callback

    def patched_callback(*args):
        with monkeypatch.context() as mp:
            mp.setitem(frozen, 0, True)
            orig_callback(*args)

    monkeypatch.setattr(junkdrawer, "_gc_callback", patched_callback)


random_states_after_tests = {}
independent_random = random.Random()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    # This hookwrapper checks for PRNG state leaks from Hypothesis tests.
    # See: https://github.com/HypothesisWorks/hypothesis/issues/1919
    if not (hasattr(item, "obj") and is_hypothesis_test(item.obj)):
        outcome = yield
    elif "pytest_randomly" in sys.modules:
        # See https://github.com/HypothesisWorks/hypothesis/issues/3041 - this
        # branch exists to make it easier on external contributors, but should
        # never run in our CI (because that would disable the check entirely).
        assert not is_in_ci()
        outcome = yield
    else:
        # We start by peturbing the state of the PRNG, because repeatedly
        # leaking PRNG state resets state_after to the (previously leaked)
        # state_before, and that just shows as "no use of random".
        random.seed(independent_random.randrange(2**32))
        before = random.getstate()
        outcome = yield
        after = random.getstate()
        if before != after:
            if after in random_states_after_tests:
                raise Exception(
                    f"{item.nodeid!r} and {random_states_after_tests[after]!r} "
                    "both used the `random` module, and finished with the "
                    "same global `random.getstate()`; this is probably a nasty bug!"
                )
            random_states_after_tests[after] = item.nodeid

    # Annotate usage of .example() with a hint about alternatives
    if isinstance(getattr(outcome, "exception", None), NonInteractiveExampleWarning):
        add_note(
            outcome.exception,
            "For hypothesis' own test suite, consider using one of the helper "
            "methods in tests.common.debug instead.",
        )
