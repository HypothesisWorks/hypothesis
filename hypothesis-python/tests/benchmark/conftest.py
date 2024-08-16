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
repeat = None  # set by pytest_configure


def stats(d):
    # stable funny-statistics:
    # throw away extreme quintiles, return the middle three as min/expected/max
    return np.array(statistics.quantiles(d, n=6)[1:-1])


@pytest.fixture
def bench(request, monkeypatch):
    seen_exc = None

    def benchmarker(test, expected_exc=None):

        def timed(f):
            nonlocal seen_exc
            before = timer()
            try:
                f()
            except BaseException as e:
                seen_exc = e
            return timer() - before

        inner_test = test.hypothesis.inner_test

        def synthetic_work():
            # Beware: This defines the unit of work. If the work changes,
            # so do the reported numbers (which are scaled by this unit).
            try:
                f = lambda i: i * i
                f.a = {}
                for i in range(500):
                    f.a[i] = f(i)
                assert not f.a
            except AssertionError:
                pass

        def wrapped_inner_test(*args, **kwargs):
            # Add some exemplary synthetic baseline work
            # This has two purposes:
            # - make the inner test take a measurable amount of time
            # - mimic "real" load so that the relative number is fairly stable
            #   under various load conditions
            # The latter is partly successful: with 100% loaded system the test
            # takes 2.5x time, the reported numbers shift by <~20%.
            nonlocal time_inner
            before = timer()
            try:
                synthetic_work()
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
                raise AssertionError(
                    f"Did not see expected {expected_exc} (got {seen_exc!r})"
                )

    return benchmarker


def pytest_addoption(parser):
    parser.addoption("--hypothesis-bench-repeats", type=int, action="store", default=5)
    parser.addoption("--hypothesis-bench-json", type=str, action="store")


def pytest_configure(config):
    global repeat
    repeat = max(5, config.option.hypothesis_bench_repeats)
    config._bench_ratios = {}


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    terminalreporter.ensure_newline()
    terminalreporter.section(
        f"overhead relative to example cost - lower is better [{repeat}it]"
    )
    for testid, (dmin, davg, dmax) in config._bench_ratios.items():
        msg = f"{davg:5.1f}   ({dmin:5.1f} --{dmax:5.1f} )   {testid}"
        terminalreporter.write_line(msg, yellow=True, bold=True)

    store_json = config.option.hypothesis_bench_json
    if store_json:
        with open(store_json, "w", encoding="utf8") as f:
            # github-actions-benchmark `customSmallerIsBetter`
            json.dump(
                [
                    {
                        "name": testid,
                        "unit": "",
                        "value": round(davg, ndigits=1),
                        "range": f"{dmin:.1f} – {dmax:.1f}",
                        # "extra": "",
                    }
                    for testid, (dmin, davg, dmax) in config._bench_ratios.items()
                ],
                f,
            )
