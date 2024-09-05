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
import re
import statistics
import time
from collections import namedtuple

import pytest

# Performance measurements on shared CI workers is notoriously unreliable. Here,
# some tricks are used to work around it:
#
# - Use the time.process_time (CPU time) timer, in an attempt to exclude the effect
#   of concurrent processes on the server.
# - Report the ratio between a fixed amount of synthetic work and @given, instead
#   of absolute times.
# - Run the test parts (synthetic/@given) interleaved many times, so that temporal
#   load fluctuations impact both parts more equally.


timer = time.process_time  # store a reference in case the time module is monkeypatched
# set by pytest_configure:
repeat = None  # repeats to run internally
count = None  # repeats as executed by pytest-repeat

ratio = namedtuple("ratio", ("p05", "p25", "p50", "p75", "p95"))


def stats(data):
    if len(data) == 1:
        return ratio(*([data[0]] * 5))
    ntiles = statistics.quantiles(data, n=20, method="inclusive")
    return ratio(ntiles[0], ntiles[4], ntiles[9], ntiles[14], ntiles[18])


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
                # there is no logic to this, just arbitrary instructions
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
            # The latter is only partly successful: with 100% loaded system the
            # test takes 2.5x time, some of the reported numbers shift by ~20%.
            # The problem is probably that the synthetic work is an imperfect
            # approximation of the actual overhead-work.
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
            assert time_given > time_inner > 0
            # Note, rel_overhead is somewhat insensitive to changes in performance
            # caused by a change in the number of inner-test executions (shrinks).
            # That's ok, since that number is tracked elsewhere.
            rel_overhead.append((time_given - time_inner) / time_inner)

        test_id = request.node.nodeid
        if count > 1:
            # We're running under pytest-repeat (which is a simple way to improve
            # interleaving of tests using `--count=N --repeat-scope=session`), so
            # mangle the id to remove pytest-repeat's parametrization.
            test_id = re.sub(r"-?[0-9]+-[0-9]+\]$", "]", test_id)
            test_id = re.sub(r"\[\]$", "", test_id)
        request.config._bench_rel_overhead.setdefault(test_id, []).extend(rel_overhead)

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
    parser.addoption("--hypothesis-bench-set-ref", action="store_true")
    parser.addoption("--hypothesis-bench-use-ref", action="store_true")


def pytest_configure(config):
    global repeat, count
    repeat = max(1, config.option.hypothesis_bench_repeats)
    count = max(1, getattr(config.option, "count", 1))
    config._bench_rel_overhead = {}


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    terminalreporter.ensure_newline()
    terminalreporter.section(
        f"overhead relative to example cost - lower is better [{repeat}it×{count}]"
    )
    ratios = [(k, stats(v)) for k, v in config._bench_rel_overhead.items()]

    if config.option.hypothesis_bench_set_ref:
        refs = config.cache.get("hypothesis-bench/medians", {})
        config.cache.set(
            "hypothesis-bench/medians", refs | {testid: r.p50 for testid, r in ratios}
        )
    if config.option.hypothesis_bench_use_ref:
        refs = config.cache.get("hypothesis-bench/medians", {})
        has_ref = refs.keys()
        ratios = [
            (testid, ratio(*[p / ref for p in ps]))
            for testid, ps in ratios
            if (ref := refs.get(testid, 1.0))
        ]
    else:
        has_ref = set()

    for testid, r in ratios:
        marker = "×" if testid in has_ref else " "
        msg = f"{marker}{r.p50:5.2f}   ({r.p05:5.2f}, {r.p95:5.2f})   {testid}"
        terminalreporter.write_line(msg, bold=True)

    store_json = config.option.hypothesis_bench_json
    if store_json:
        with open(store_json, "w", encoding="utf8") as f:
            # github-actions-benchmark `customSmallerIsBetter`
            json.dump(
                [
                    {
                        "name": testid,
                        "unit": "",
                        "value": round(r.p50, ndigits=2),
                        "range": f"{r.p05:.2f} – {r.p95:.2f}",
                        "extra": f"interquartile range {r.p25:.2f} – {r.p75:.2f}",
                    }
                    for testid, r in ratios
                ],
                f,
            )
