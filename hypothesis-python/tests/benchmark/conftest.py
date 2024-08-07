import contextlib
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
def bench(request):

    def benchmarker(test, exc=None):
        repeat = max(5, request.config.option.hypothesis_bench_repeats)

        def timed(f, number):
            before = timer()
            for _ in range(number):
                with contextlib.suppress(exc) if exc else contextlib.nullcontext():
                    f()
            return timer() - before

        def single_synthetic_example():
            # add some exemplary synthetic baseline work (build a dict from a
            # lambda fn with some getattrs mixed in, raise and catch an exception,
            # plus the context manager inside timed)
            try:
                f = lambda i: i * i
                f.a = {}
                for i in range(500):
                    f.a[i] = f(i)
                assert not f.a
            except AssertionError:
                pass

        time_inner = []
        time_given = []
        max_examples = test._hypothesis_internal_use_settings.max_examples

        for _ in range(repeat):
            # interleave measurements to smoothen effect of varying load
            time_inner.append(timed(single_synthetic_example, number=max_examples))
            time_given.append(timed(test, number=1))
        ratio = stats(np.array(time_given) / np.array(time_inner))

        request.config._bench_ratios[request.node.nodeid] = ratio

        # Verify that we got our exception
        if exc is not None:
            try:
                test()
            except exc:
                pass
            else:
                raise AssertionError(f"Did not see expected {exc}")

    return benchmarker


def pytest_addoption(parser):
    parser.addoption("--hypothesis-bench-repeats", type=int, action="store", default=5)


def pytest_configure(config):
    config._bench_ratios = {}


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    terminalreporter.ensure_newline()
    terminalreporter.section(
        "relative overhead (per example) - lower is better"
    )
    for testid, (dmin, davg, dmax) in config._bench_ratios.items():
        msg = f"{davg:5.1f}   ({dmin:5.1f} --{dmax:5.1f} )   {testid}"
        terminalreporter.write_line(msg, yellow=True, bold=True)

    proc = subprocess.run(["git", "show", "--summary", "HEAD^"], capture_output=True, encoding="utf8")
    with open("bench.json", "w") as f:
        # github-actions-benchmark `customSmallerIsBetter`
        json.dump([
            {
                "name": testid,
                "unit": "ratio",
                "value": davg,
                "range": [dmin, dmax],
                "extra": proc.stdout,
            }
            for testid, (dmin, davg, dmax) in config._bench_ratios.items()
        ], f)
