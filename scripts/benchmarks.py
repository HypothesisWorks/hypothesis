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
import json
import math
import zlib
import base64
import random
import hashlib
from collections import OrderedDict

import numpy as np

import attr
import click
import hypothesis.strategies as st
from hypothesis import settings
from scipy.stats import wilcoxon
from hypothesis.errors import UnsatisfiedAssumption
from hypothesis.internal.conjecture.data import Status
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


@attr.s()
class BenchmarkData(object):
    data = attr.ib()
    seed = attr.ib()

    @property
    def sizes(self):
        return [d.size for d in self.data]

    def is_identical(self, other):
        n = min(len(self.data), len(other.data))
        return self.data[:n] == other.data[:n]


@attr.s()
class SingleBenchmarkResult(object):
    size = attr.ib()
    success = attr.ib()
    success_size = attr.ib()


STRATEGIES = OrderedDict([
    ('ints', st.integers()),
    ('intlists', st.lists(st.integers())),
])


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


usually = sometimes(0.9, 'usually')


def minsum(seed, testdata, value):
    return sum(value) >= 1000


def has_duplicates(seed, testdata, value):
    return len(set(value)) < len(value)


for k in STRATEGIES:
    define_benchmark(k, always, never)
    define_benchmark(k, always, always)
    define_benchmark(k, always, usually)


define_benchmark('intlists', always, minsum)
define_benchmark('intlists', always, has_duplicates)
define_benchmark('intlists', has_duplicates, minsum)

# BENCHMARK DEFINITIONS END

# From here on out it's gory definitions of how the benchmarks are actually
# run.


def random_for_int(i):
    """Use hashing to give a better seed starting from an integer (random
    module gives no guarantees that similar seeds will give very different
    results)"""
    encoded = i.to_bytes(i.bit_length() // 8 + 1, 'big')
    hashed = hashlib.sha1(encoded).digest()
    seed = int.from_bytes(hashed, 'big')
    return random.Random(seed)


def run_benchmark(benchmark, n_runs, base_seed):
    click.echo('Calculating data for %s' % (benchmark.name,))
    results = []

    # We seed our test functions deterministically so that when comparing two
    # benchmarks on different runs at the same index we get exactly the same
    # values.
    test_seed_generator = random.Random(0)

    run_seed_generator = random_for_int(base_seed)

    with click.progressbar(range(n_runs)) as runs:
        for _ in runs:
            sizes = []
            valid_seed = test_seed_generator.getrandbits(64).to_bytes(8, 'big')
            interesting_seed = test_seed_generator.getrandbits(64).to_bytes(
                8, 'big')

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
                test_function, settings=BENCHMARK_SETTINGS,
                random=random.Random(run_seed_generator.getrandbits(64)),
            )
            engine.run()
            assert len(sizes) > 0
            success = int(engine.last_data.status == Status.INTERESTING)
            success_size = None if not success else len(
                engine.last_data.buffer)
            results.append(
                SingleBenchmarkResult(
                    size=sum(sizes),
                    success=success,
                    success_size=success_size,
                )
            )
    return BenchmarkData(data=results, seed=base_seed)


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
    as_json = json.dumps(attr.asdict(data)).encode('utf-8')
    compressed = zlib.compress(as_json)
    as_base64 = base64.b32encode(compressed)
    return as_base64.decode('ascii')


def blob_to_data(blob):
    from_base64 = base64.b32decode(blob.encode('ascii'))
    decompressed = zlib.decompress(from_base64)
    parsed = json.loads(decompressed)
    return BenchmarkData(
        data=[SingleBenchmarkResult(**p) for p in parsed['data']],
        seed=parsed['seed'],
    )


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
# This benchmark was generated with seed %(seed)d
#
# Key statistics for this benchmark:
#
# * %(count)d runs, of which %(discovery)s succeeded.
# * Mean size: %(mean).2f bytes, standard deviation: %(sd).2f bytes
# * Mean shrunk size: %(shrunk_size)s
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
    sizes = [d.size for d in new_data.data]
    discovery = sum(d.success for d in new_data.data)
    shrunk_size = 'N/A' if not discovery else str(np.mean([
        d.success_size for d in new_data.data if d.success
    ]))
    with open(benchmark_file(name), 'w') as o:
        o.write(BENCHMARK_HEADER % {
            'strategy_name': strategy_name,
            'strategy': benchmark.strategy,
            'valid': benchmark.valid.__name__,
            'interesting': benchmark.interesting.__name__,
            'seed': new_data.seed,
            'count': len(sizes),
            'discovery': discovery,
            'mean': np.mean(sizes),
            'shrunk_size': shrunk_size,
            'min': min(sizes),
            'nmin': times(sizes.count(min(sizes))),
            'nmax': times(sizes.count(max(sizes))),
            'max': max(sizes),
            'sd': np.std(sizes),
            'median': int(np.percentile(sizes, 50, interpolation='lower')),
            'lo': int(np.percentile(sizes, 1, interpolation='lower')),
            'hi': int(np.percentile(sizes, 99, interpolation='higher')),
        })
        o.write('\n')
        o.write('\n')
        blob = data_to_blob(new_data)
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


@attr.s
class Report(object):
    name = attr.ib()
    target = attr.ib()
    p = attr.ib()
    old_mean = attr.ib()
    new_mean = attr.ib()
    new_data = attr.ib()


DEFAULT_RUNS = 200


@click.command()
@click.option(
    '--nruns', default=None, type=int, help="""
Specify the number of runs of each benchmark to perform. If this is larger than
the number of stored runs then this will result in the existing data treated as
if it were non-existing. If it is smaller, the existing data will be sampled.
""")
@click.argument('benchmarks', nargs=-1)
@click.option('--check/--no-check', default=False)
@click.option('--skip-existing/--no-skip-existing', default=False)
@click.option('--fdr', default=0.001)
@click.option('--update', type=click.Choice([
    NONE, NEW, ALL, CHANGED,
]), default=NEW)
@click.option('--only-update-headers/--full-run', default=False)
def cli(
    benchmarks, nruns, check, update, fdr, skip_existing,
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
            old_data = existing_data(name)
            new_data = run_benchmark(
                BENCHMARKS[name],
                len(old_data.data) if nruns is None else nruns,
                old_data.seed + 1)

            for target in ('size', 'success', 'success_size'):

                old_values = []
                new_values = []
                for d_old, d_new in zip(old_data.data, new_data.data):
                    v_old = getattr(d_old, target)
                    v_new = getattr(d_new, target)
                    if v_old is not None and v_new is not None:
                        old_values.append(v_old)
                        new_values.append(v_new)
                assert len(old_values) == len(new_values)
                differences = sum(
                    u != v for u, v in zip(old_values, new_values))
                if differences <= 20:
                    click.echo((
                        'Skipping %s in %s due to %d < 20 '
                        'different examples') % (target, name, differences))
                    continue

                pp = wilcoxon(old_values, new_values)[1]
                assert not math.isnan(pp)
                click.echo('p-value for difference in %s %.5f' % (target, pp,))
                reports.append(Report(
                    name, target, pp, np.mean(old_values), np.mean(new_values),
                    new_data,
                ))
            if update == ALL:
                write_data(name, new_data)
        elif update != NONE:
            new_data = run_benchmark(
                BENCHMARKS[name], DEFAULT_RUNS if nruns is None else nruns, 0)
            write_data(name, new_data)

    if not reports:
        sys.exit(0)

    click.echo('Checking for different means')

    # We now perform a Benjamini-Hochberg-Yekutieli test. This gives us a list
    # of possibly significant differences while controlling the false discovery
    # rate. https://en.wikipedia.org/wiki/False_discovery_rate
    reports.sort(key=lambda x: x.p)

    threshold = 0
    n = len(reports)
    harmonic = 0
    for k, report in enumerate(reports, 1):
        # The harmonic numbers are needed to adjust for the fact that our
        # different tests are not independent and are of uncertain correlation.
        harmonic += 1 / k
        if report.p <= k * fdr / (n * harmonic):
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
            click.echo('Different means for %s in %s: %.2f -> %.2f. p=%.5f' % (
                report.target, report.name, report.old_mean, report.new_mean,
                report.p
            ))
        if check:
            sys.exit(1)
        if update == CHANGED:
            for name, data in {r.name: r.new_data for r in different}.items():
                write_data(name, data)
    else:
        click.echo('No significant differences')


if __name__ == '__main__':
    cli()
