# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

# pylint: skip-file

from __future__ import division, print_function, absolute_import

from collections import OrderedDict
import attr
import hypothesis.strategies as st
from hypothesis import settings
from hypothesis.internal.conjecture.engine import ConjectureRunner
from hypothesis.internal.conjecture.data import StopTest
from hypothesis.errors import UnsatisfiedAssumption
from scipy.stats import ttest_ind
import click
import os
import random
import hashlib
import numpy as np
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


DATA_DIR = os.path.join(
    ROOT,
    "benchmark-data",
)


BENCHMARK_SETTINGS = settings(
    max_examples=200, max_iterations=1000, max_shrinks=1000,
    database=None, timeout=-1,
)


BENCHMARKS = OrderedDict()


@attr.s()
class Benchmark(object):
    name = attr.ib()
    strategy = attr.ib()
    valid = attr.ib()
    failing = attr.ib()


STRATEGIES = {
    'intlists': st.lists(st.integers())
}


def define_benchmark(strategy_name, valid, failing):
    name = "%s-valid=%s-interesting=%s" % (
        strategy_name, valid.__name__, failing.__name__)
    assert name not in BENCHMARKS
    strategy = STRATEGIES[strategy_name]
    BENCHMARKS[name] = Benchmark(name, strategy, valid, failing)


def always(seed, testdata, value):
    return True


def never(seed, testdata, value):
    return False


def sometimes(p, name=None):
    def accept(seed, testdata, value):
        hasher = hashlib.md5()
        hasher.update(testdata.buffer)
        hasher.update(seed)
        return random.Random(hasher.digest()).random() <= p
    accept.__name__ = name or 'sometimes(%r)' % (p,)
    return accept


rarely = sometimes(0.1, "rarely")
usually = sometimes(0.9, "usually")


def minsum(seed, testdata, value):
    return sum(value) >= 1000


define_benchmark("intlists", always, never)
define_benchmark("intlists", always, always)
define_benchmark("intlists", always, rarely)
define_benchmark("intlists", always, minsum)
define_benchmark("intlists", minsum, never)
define_benchmark("intlists", rarely, never)
define_benchmark("intlists", usually, usually)


def run_benchmark_for_sizes(benchmark, n_runs):
    click.echo("Calculating data for %s" % (benchmark.name,))
    total_sizes = []

    with click.progressbar(range(n_runs)) as runs:
        for _ in runs:
            sizes = []
            valid_seed = random.getrandbits(64).to_bytes(8, 'big')
            failing_seed = random.getrandbits(64).to_bytes(8, 'big')

            def test_function(data):
                try:
                    try:
                        value = data.draw(benchmark.strategy)
                    except UnsatisfiedAssumption:
                        data.mark_invalid()
                    if not data.frozen:
                        if not benchmark.valid(valid_seed, data, value):
                            data.mark_invalid()
                        if benchmark.failing(failing_seed, data, value):
                            data.mark_interesting()
                except StopTest:
                    pass
                sizes.append(len(data.buffer))
            engine = ConjectureRunner(
                test_function, settings=BENCHMARK_SETTINGS, random=random
            )
            engine.run()
            assert len(sizes) > 0
            total_sizes.append(sum(sizes))
    return total_sizes


def benchmark_difference_p_value(existing, recent):
    return ttest_ind(existing, recent, equal_var=False)[1]


def benchmark_file(name):
    return os.path.join(DATA_DIR, name)


def have_existing_data(name):
    return os.path.exists(benchmark_file(name))


EXISTING_CACHE = {}


def existing_data(name):
    try:
        return EXISTING_CACHE[name]
    except KeyError:
        pass

    fname = benchmark_file(name)
    result = []
    with open(fname) as i:
        for l in i:
            k, n = l.strip().split(": ")
            k = int(k)
            for _ in range(int(n)):
                result.append(k)
    EXISTING_CACHE[name] = result
    return result


def write_data(name, new_data):
    counts = Counter(new_data)
    with open(benchmark_file(name), 'w') as o:
        for k, n in sorted(
            counts.items(), reverse=True, key=lambda x: (x[1], x[0])
        ):
            o.write("%d: %d\n" % (k, n))


NONE = "none"
NEW = "new"
ALL = "all"
CHANGED = "changed"
IMPROVED = "improved"


@attr.s
class Report(object):
    name = attr.ib()
    p = attr.ib()
    old_mean = attr.ib()
    new_mean = attr.ib()
    new_data = attr.ib()


@click.command()
@click.option(
    "--seed", default=0, help="Set a different random seed for the run"
)
@click.option(
    "--nruns", default=200, type=int, help="""
Specify the number of runs of each benchmark to perform. If this is larger than
the number of stored runs then this will result in the existing data treated as
if it were non-existing. If it is smaller, the existing data will be sampled.
""")
@click.argument('benchmarks', nargs=-1)
@click.option('--check/--no-check', default=False)
@click.option('--skip-existing/--no-skip-existing', default=False)
@click.option('--fdr', default=0.001)
@click.option('--update', type=click.Choice([
    NONE, NEW, ALL, CHANGED, IMPROVED
]), default=NEW)
def cli(seed, benchmarks, nruns, check, update, fdr, skip_existing):
    """
    This is the benchmark runner script for Hypothesis. Rather than running
    benchmarks by *time* this runs benchmarks by *amount of data*. This is
    the major determiner of performance in Hypothesis (other than speed of the
    end user's tests) and has the important property that we can benchmark it
    without reference to the underlying system's performance.
    """

    if check:
        if update not in [NONE, NEW]:
            raise click.UsageError("check and update cannot be used together")
        if skip_existing:
            raise click.UsageError(
                "check and skip-existing cannot be used together")

    for name in benchmarks:
        if name not in BENCHMARKS:
            raise click.UsageError("Invalid benchmark name %s" % (name,))

    random.seed(seed)
    try:
        os.mkdir(DATA_DIR)
    except FileExistsError:
        pass

    reports = []
    if check:
        for name in benchmarks or BENCHMARKS:
            if not have_existing_data(name):
                click.echo("No existing data for benchmark %s" % (
                    name,
                ))
                sys.exit(1)

    for name in benchmarks or BENCHMARKS:
        if have_existing_data(name):
            if skip_existing:
                continue
            new_data = run_benchmark_for_sizes(BENCHMARKS[name], nruns)

            old_data = existing_data(name)

            pp = benchmark_difference_p_value(old_data, new_data)
            click.echo("p-value for difference %.5f" % (pp,))
            reports.append(Report(
                name, pp, np.mean(old_data), np.mean(new_data), new_data
            ))
            if update == ALL:
                write_data(name, new_data)
        elif update != NONE:
            new_data = run_benchmark_for_sizes(BENCHMARKS[name], nruns)

            write_data(name, new_data)

    if not reports:
        sys.exit(0)

    click.echo("Checking for different means")

    reports.sort(key=lambda x: x.p)

    threshold = 0
    n = len(reports)
    for k, report in enumerate(reports, 1):
        if report.p <= k * fdr / n:
            assert report.p <= fdr
            threshold = k
    different = reports[:threshold]

    if threshold > 0:
        click.echo((
            "Found %d benchmark%s with significant difference "
            "at false discovery rate %r"
        ) % (
            threshold,
            "s" if threshold > 1 else "",
            fdr,
        ))

    if different:
        for report in different:
            click.echo("Different means for %s: %.2f -> %.2f. p=%.5f" % (
                report.name, report.old_mean, report.new_mean, report.p
            ))
        if check:
            sys.exit(1)
        for r in different:
            if update == CHANGED:
                write_data(r.name, r.new_data)
            elif update == IMPROVED and r.new_mean < r.old_mean:
                write_data(r.name, r.new_data)
    else:
        click.echo("No significant differences")


if __name__ == '__main__':
    cli()
