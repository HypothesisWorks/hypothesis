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

import os
import sys
import gzip
import json
import base64
import random
import hashlib
from collections import OrderedDict

import numpy as np

import attr
import click
import hypothesis.strategies as st
from hypothesis import settings
from scipy.stats import ttest_ind
from hypothesis.errors import UnsatisfiedAssumption
from hypothesis.internal.conjecture.engine import ConjectureRunner

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


DATA_DIR = os.path.join(
    ROOT,
    'benchmark-data',
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
    interesting = attr.ib()


STRATEGIES = {
    'intlists': st.lists(st.integers())
}


def define_benchmark(strategy_name, valid, interesting):
    name = '%s-valid=%s-interesting=%s' % (
        strategy_name, valid.__name__, interesting.__name__)
    assert name not in BENCHMARKS
    strategy = STRATEGIES[strategy_name]
    BENCHMARKS[name] = Benchmark(name, strategy, valid, interesting)


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


rarely = sometimes(0.1, 'rarely')
usually = sometimes(0.9, 'usually')


def minsum(seed, testdata, value):
    return sum(value) >= 1000


define_benchmark('intlists', always, never)
define_benchmark('intlists', always, always)
define_benchmark('intlists', always, rarely)
define_benchmark('intlists', always, minsum)
define_benchmark('intlists', minsum, never)
define_benchmark('intlists', rarely, never)
define_benchmark('intlists', usually, usually)


def run_benchmark_for_sizes(benchmark, n_runs):
    click.echo('Calculating data for %s' % (benchmark.name,))
    total_sizes = []

    with click.progressbar(range(n_runs)) as runs:
        for _ in runs:
            sizes = []
            valid_seed = random.getrandbits(64).to_bytes(8, 'big')
            interesting_seed = random.getrandbits(64).to_bytes(8, 'big')

            def test_function(data):
                try:
                    try:
                        value = data.draw(benchmark.strategy)
                    except UnsatisfiedAssumption:
                        data.mark_invalid()
                    if not data.frozen:
                        if not benchmark.valid(valid_seed, data, value):
                            data.mark_invalid()
                        if benchmark.interesting(
                            interesting_seed, data, value
                        ):
                            data.mark_interesting()
                finally:
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


BLOBSTART = 'START'
BLOBEND = 'END'


def existing_data(name):
    try:
        return EXISTING_CACHE[name]
    except KeyError:
        pass

    fname = benchmark_file(name)
    result = None
    with open(fname) as i:
        for l in i:
            l = l.strip()
            if not l:
                continue
            if l.startswith('#'):
                continue
            key, blob = l.split(': ', 1)
            magic, n = key.split(' ')
            assert magic == 'Data'
            n = int(n)
            assert blob.startswith(BLOBSTART)
            assert blob.endswith(BLOBEND), blob[-len(BLOBEND) * 2:]
            assert len(blob) == n + len(BLOBSTART) + len(BLOBEND)
            blob = blob[len(BLOBSTART):len(blob) - len(BLOBEND)]
            assert len(blob) == n
            result = blob_to_data(blob)
            break
    assert result is not None
    EXISTING_CACHE[name] = result
    return result


def data_to_blob(data):
    as_json = json.dumps(data).encode('utf-8')
    compressed = gzip.compress(as_json)
    as_base64 = base64.b32encode(compressed)
    return as_base64.decode('ascii')


def blob_to_data(blob):
    from_base64 = base64.b32decode(blob.encode('ascii'))
    decompressed = gzip.decompress(from_base64)
    return json.loads(decompressed)


BENCHMARK_HEADER = """
# This is an automatically generated file from Hypothesis's benchmarking
# script (scripts/benchmarks.py).
#
# Lines like this starting with a # are designed to be useful for human
# consumption when reviewing, specifically with a goal of producing
# useful diffs so that you can get a sense of the impact of a change.
#
# This benchmark is for %(strategy_name)s [%(strategy)r], with the validity
# condition "%(valid)s" and the interestingness condition "%(interesting)s".
# See the script for the exact definitions of these criteria.
#
# Key statistics for this benchmark:
#
# * %(count)d examples
# * Mean size: %(mean).2f bytes, standard deviation: %(sd).2f bytes
#
# Additional interesting statistics:
#
# * Ranging from %(min)d [%(nmin)s] to %(max)d [%(nmax)s] bytes.
# * Median size: %(median)d
# * 99%% of examples had at least %(lo)d bytes
# * 99%% of examples had at most %(hi)d bytes
#
# All data after this point is an opaque binary blob. You are not expected
# to understand it.
""".strip()


def times(n):
    assert n > 0
    if n > 1:
        return '%d times' % (n,)
    else:
        return 'once'


def write_data(name, new_data):
    benchmark = BENCHMARKS[name]
    strategy_name = [
        k for k, v in STRATEGIES.items() if v == benchmark.strategy
    ][0]
    with open(benchmark_file(name), 'w') as o:
        o.write(BENCHMARK_HEADER % {
            'strategy_name': strategy_name,
            'strategy': benchmark.strategy,
            'valid': benchmark.valid.__name__,
            'interesting': benchmark.interesting.__name__,
            'count': len(new_data),
            'min': min(new_data),
            'nmin': times(new_data.count(min(new_data))),
            'nmax': times(new_data.count(max(new_data))),
            'max': max(new_data),
            'mean': np.mean(new_data),
            'sd': np.std(new_data),
            'median': int(np.percentile(new_data, 50, interpolation='lower')),
            'lo': int(np.percentile(new_data, 1, interpolation='lower')),
            'hi': int(np.percentile(new_data, 99, interpolation='higher')),
        })
        o.write('\n')
        o.write('\n')
        blob = data_to_blob(sorted(new_data))
        assert '\n' not in blob
        o.write('Data %d: ' % (len(blob),))
        o.write(BLOBSTART)
        o.write(blob)
        o.write(BLOBEND)
        o.write('\n')


NONE = 'none'
NEW = 'new'
ALL = 'all'
CHANGED = 'changed'
IMPROVED = 'improved'


@attr.s
class Report(object):
    name = attr.ib()
    p = attr.ib()
    old_mean = attr.ib()
    new_mean = attr.ib()
    new_data = attr.ib()


@click.command()
@click.option(
    '--seed', default=0, help='Set a different random seed for the run'
)
@click.option(
    '--nruns', default=200, type=int, help="""
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
@click.option('--only-update-headers/--full-run', default=False)
def cli(
    seed, benchmarks, nruns, check, update, fdr, skip_existing,
    only_update_headers,
):
    """This is the benchmark runner script for Hypothesis.

    Rather than running benchmarks by *time* this runs benchmarks by
    *amount of data*. This is the major determiner of performance in
    Hypothesis (other than speed of the end user's tests) and has the
    important property that we can benchmark it without reference to the
    underlying system's performance.

    """

    if check:
        if update not in [NONE, NEW]:
            raise click.UsageError('check and update cannot be used together')
        if skip_existing:
            raise click.UsageError(
                'check and skip-existing cannot be used together')
        if only_update_headers:
            raise click.UsageError(
                'check and rewrite-only cannot be used together')

    if only_update_headers:
        for name in BENCHMARKS:
            if have_existing_data(name):
                write_data(name, existing_data(name))
        sys.exit(0)

    for name in benchmarks:
        if name not in BENCHMARKS:
            raise click.UsageError('Invalid benchmark name %s' % (name,))

    random.seed(seed)
    try:
        os.mkdir(DATA_DIR)
    except FileExistsError:
        pass

    reports = []
    if check:
        for name in benchmarks or BENCHMARKS:
            if not have_existing_data(name):
                click.echo('No existing data for benchmark %s' % (
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
            click.echo('p-value for difference %.5f' % (pp,))
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

    click.echo('Checking for different means')

    # We now perform a Benjamini Hochberg test. This gives us a list of
    # possibly significant differences while controlling the false discovery
    # rate. https://en.wikipedia.org/wiki/False_discovery_rate
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
            'Found %d benchmark%s with significant difference '
            'at false discovery rate %r'
        ) % (
            threshold,
            's' if threshold > 1 else '',
            fdr,
        ))

    if different:
        for report in different:
            click.echo('Different means for %s: %.2f -> %.2f. p=%.5f' % (
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
        click.echo('No significant differences')


if __name__ == '__main__':
    cli()
