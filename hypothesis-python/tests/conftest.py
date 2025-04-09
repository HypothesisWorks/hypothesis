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
import inspect
import json
import os
import random
import sys
import time as time_module
from functools import wraps
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

from hypothesis import is_hypothesis_test
from hypothesis._settings import is_in_ci
from hypothesis.errors import NonInteractiveExampleWarning
from hypothesis.internal.compat import add_note
from hypothesis.internal.conjecture import junkdrawer

from tests.common import TIME_INCREMENT
from tests.common.setup import run
from tests.common.utils import raises_warning

run()

# Skip collection of tests which require the Django test runner,
# or that don't work on the current version of Python.
collect_ignore_glob = ["django/*"]
if sys.version_info < (3, 10):
    collect_ignore_glob.append("cover/*py310*")
if sys.version_info < (3, 12):
    collect_ignore_glob.append("cover/*py312*.py")

if sys.version_info >= (3, 11):
    collect_ignore_glob.append("cover/test_asyncio.py")  # @asyncio.coroutine removed


in_shrinking_benchmark = False


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: pandas expects this marker to exist.")
    config.addinivalue_line(
        "markers",
        "xp_min_version(api_version): run when greater or equal to api_version",
    )
    config.addinivalue_line("markers", "xf_crosshair: selection for xfailing symbolics")

    if config.getoption("--hypothesis-benchmark-shrinks"):
        # we'd like to support xdist here, but a session-scope fixture won't
        # be enough: https://github.com/pytest-dev/pytest-xdist/issues/271.
        # Need a lockfile or equivalent.

        assert config.getoption(
            "--hypothesis-benchmark-output"
        ), "must specify shrinking output file"

        global in_shrinking_benchmark
        in_shrinking_benchmark = True


def pytest_addoption(parser):
    parser.addoption("--hypothesis-update-outputs", action="store_true")
    parser.addoption("--hypothesis-benchmark-shrinks", type=str, choices=["new", "old"])
    parser.addoption("--hypothesis-benchmark-output", type=str)

    # New in pytest 6, so we add a shim on old versions to avoid missing-arg errors
    arg = "--durations-min"
    if arg not in sum((a._long_opts for g in parser._groups for a in g.options), []):
        parser.addoption(arg, action="store", default=1.0)


@pytest.fixture(scope="function", params=["warns", "raises"])
def warns_or_raises(request):
    """This runs the test twice: first to check that a warning is emitted
    and execution continues successfully despite the warning; then to check
    that the raised warning is handled properly.
    """
    if request.param == "raises":
        return raises_warning
    else:
        return pytest.warns


# crosshair needs actual time for its path timeouts; load it before patching
try:
    import hypothesis_crosshair_provider.crosshair_provider  # noqa: F401
except ImportError:
    pass


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
    frozen = False

    current_time = time_module.time()

    def time():
        nonlocal current_time
        if not frozen:
            current_time += TIME_INCREMENT
        return current_time

    def sleep(naptime):
        nonlocal current_time
        current_time += naptime

    def freeze():
        nonlocal frozen
        frozen = True

    def _patch(name, fn):
        monkeypatch.setattr(time_module, name, wraps(getattr(time_module, name))(fn))

    _patch("time", time)
    _patch("monotonic", time)
    _patch("perf_counter", time)
    _patch("sleep", sleep)
    monkeypatch.setattr(time_module, "freeze", freeze, raising=False)

    # In the patched time regime, observing it causes it to increment. To avoid reintroducing
    # non-determinism due to GC running at arbitrary times, we patch the GC observer
    # to NOT increment time.

    monkeypatch.setattr(junkdrawer, "_perf_counter", time)

    if hasattr(gc, "callbacks"):
        # ensure timer callback is added, then bracket it by freeze/unfreeze below
        junkdrawer.gc_cumulative_time()

        _was_frozen = False

        def _freezer(*_):
            nonlocal _was_frozen, frozen
            _was_frozen = frozen
            frozen = True

        def _unfreezer(*_):
            nonlocal _was_frozen, frozen
            frozen = _was_frozen

        gc.callbacks.insert(0, _freezer)  # freeze before gc callback
        gc.callbacks.append(_unfreezer)  # unfreeze after

        yield

        assert gc.callbacks.pop(0) == _freezer
        assert gc.callbacks.pop() == _unfreezer
    else:  # pragma: no cover # branch never taken in CPython
        yield


random_states_after_tests = {}
independent_random = random.Random()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    if item.config.getoption("--hypothesis-benchmark-shrinks"):
        yield from _benchmark_shrinks(item)
        # ideally benchmark shrinking would not be mutually exclusive with the
        # other checks in this function, but it's cleaner to early-return here,
        # and in practice they will error in normal tests before one runs a
        # benchmark.
        return
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


timer = time_module.process_time


def _worker_path(session: pytest.Session) -> Path:
    return (
        Path(session.config.getoption("--hypothesis-benchmark-output")).parent
        # https://pytest-xdist.readthedocs.io/en/stable/how-to.html#envvar-PYTEST_XDIST_WORKER
        / f"shrinking_results_{os.environ['PYTEST_XDIST_WORKER']}.json"
    )


def _benchmark_shrinks(item: pytest.Function) -> None:
    from hypothesis.internal.conjecture.shrinker import Shrinker

    # this isn't perfect, but it is cheap!
    if "minimal(" not in inspect.getsource(item.function):
        pytest.skip("(probably) does not call minimal()")

    actual_shrink = Shrinker.shrink
    shrink_calls = []
    shrink_time = []

    def shrink(self, *args, **kwargs):
        nonlocal shrink_calls
        nonlocal shrink_time
        start_t = timer()
        result = actual_shrink(self, *args, **kwargs)
        shrink_calls.append(self.engine.call_count - self.initial_calls)
        shrink_time.append(timer() - start_t)
        return result

    monkeypatch = MonkeyPatch()
    monkeypatch.setattr(Shrinker, "shrink", shrink)

    # pytest_runtest_call must yield at some point. This executes the test function
    # n - 1 times, and then yields for the final execution.
    for _ in range(5 - 1):
        item.runtest()
    yield

    monkeypatch.undo()

    # remove leading hypothesis-python/tests/...
    nodeid = item.nodeid.rsplit("/", 1)[1]

    results_p = _worker_path(item.session)
    if not results_p.exists():
        results_p.write_text(json.dumps({"calls": {}, "time": {}}))

    data = json.loads(results_p.read_text())
    data["calls"][nodeid] = shrink_calls
    data["time"][nodeid] = shrink_time
    results_p.write_text(json.dumps(data))


def pytest_sessionfinish(session, exitstatus):
    if not (mode := session.config.getoption("--hypothesis-benchmark-shrinks")):
        return
    # only run on the controller process, not the workers
    if hasattr(session.config, "workerinput"):
        return

    results = {"calls": {}, "time": {}}
    output_p = Path(session.config.getoption("--hypothesis-benchmark-output"))
    for p in output_p.parent.iterdir():
        if p.name.startswith("shrinking_results_"):
            worker_results = json.loads(p.read_text())
            results["calls"] |= worker_results["calls"]
            results["time"] |= worker_results["time"]
            p.unlink()

    results = {mode: results}
    if not output_p.exists():
        output_p.write_text(json.dumps(results))
    else:
        data = json.loads(output_p.read_text())
        data[mode] = results[mode]
        output_p.write_text(json.dumps(data))
