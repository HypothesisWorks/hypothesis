# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import json
import statistics
import subprocess
import time

import numpy as np
import pytest

# Performance measurements on shared CI workers is notoriously unreliable. Here,
# some tricks are used to work around it:
#
# - Use the time.process_time (CPU time) timer, in an attempt to exclude the effect
#   of uncontrolled concurrent processes on the server.
# - Report the ratio between a fixed amount of synthetic work and @given, instead
#   of absolute times.
# - Run the test parts (synthetic/@given) interleaved many times, so that temporal
#   load fluctuations impact both parts more equally.


timer = time.process_time  # store a reference in case the time module is monkeypatched


def stats(d):
    # stable funny-statistics:
    # throw away extreme quintiles, return the middle three as min/expected/max
    return np.array(statistics.quantiles(d, n=6)[1:-1])


@pytest.fixture
def bench(request, monkeypatch):
    seen_exc = None

    def benchmarker(test, expected_exc=None):
        repeat = max(5, request.config.option.hypothesis_bench_repeats)

        def timed(f):
            nonlocal seen_exc
            before = timer()
            try:
                f()
            except BaseException as e:
                seen_exc = e
            return timer() - before

        inner_test = test.hypothesis.inner_test

        def wrapped_inner_test(*args, **kwargs):
            # Add some exemplary synthetic baseline work (build a dict from a
            # lambda fn with some getattrs mixed in, raise and catch an exception).
            # This has two purposes:
            # - make the inner test take a measurable amount of time
            # - mimic "real" load so that the relative number is fairly stable
            #   under various load conditions
            nonlocal time_inner
            before = timer()
            try:
                f = lambda i: i * i
                f.a = {}
                for i in range(500):
                    f.a[i] = f(i)
                assert not f.a
            except AssertionError:
                pass
            try:
                inner_test(*args, **kwargs)
            finally:
                time_inner += timer() - before

        monkeypatch.setattr(test.hypothesis, "inner_test", wrapped_inner_test)

        rel_overhead = []
        for _ in range(repeat):
            time_inner = 0
            time_given = timed(test)
            assert time_inner > 0
            rel_overhead.append((time_given - time_inner) / time_inner)
        ratio = stats(rel_overhead)

        request.config._bench_ratios[request.node.nodeid] = ratio

        if expected_exc is None:
            if seen_exc is not None:
                raise seen_exc
        else:
            if not isinstance(seen_exc, expected_exc):
                raise AssertionError(f"Did not see expected {expected_exc} (got {repr(seen_exc)})")

    return benchmarker


def pytest_addoption(parser):
    parser.addoption("--hypothesis-bench-repeats", type=int, action="store", default=5)


def pytest_configure(config):
    config._bench_ratios = {}


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    terminalreporter.ensure_newline()
    terminalreporter.section("relative overhead (per example) - lower is better")
    for testid, (dmin, davg, dmax) in config._bench_ratios.items():
        msg = f"{davg:5.1f}   ({dmin:5.1f} --{dmax:5.1f} )   {testid}"
        terminalreporter.write_line(msg, yellow=True, bold=True)

    proc = subprocess.run(
        ["git", "show", "--summary", "HEAD^"], capture_output=True, encoding="utf8"
    )
    with open("bench.json", "w") as f:
        # github-actions-benchmark `customSmallerIsBetter`
        json.dump(
            [
                {
                    "name": testid,
                    "unit": "ratio",
                    "value": davg,
                    "range": [dmin, dmax],
                    "extra": proc.stdout,
                }
                for testid, (dmin, davg, dmax) in config._bench_ratios.items()
            ],
            f,
        )
