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
import zlib
import base64
import random
import hashlib
from collections import OrderedDict

import attr
import click
import numpy as np

import hypothesis.strategies as st
import hypothesis.extra.numpy as npst
from hypothesis import settings, unlimited
from hypothesis.errors import UnsatisfiedAssumption
from hypothesis.internal.conjecture.engine import ConjectureRunner

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


DATA_DIR = os.path.join(
    ROOT,
    'benchmark-data',
)


BENCHMARK_SETTINGS = settings(
    max_examples=200, max_iterations=1000, max_shrinks=1000,
    database=None, timeout=unlimited, use_coverage=False,
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
    sizes = attr.ib()
    seed = attr.ib(default=0)


STRATEGIES = OrderedDict([
    ('ints', st.integers()),
    ('intlists', st.lists(st.integers())),
    ('sizedintlists', st.integers(0, 10).flatmap(
        lambda n: st.lists(st.integers(), min_size=n, max_size=n))),
    ('text', st.text()),
    ('text5', st.text(min_size=5)),
    ('arrays10', npst.arrays('int8', 10)),
    ('arraysvar', npst.arrays('int8', st.integers(0, 10))),
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


def nontrivial(seed, testdata, value):
    return sum(testdata.buffer) >= 255


def sometimes(p, name=None):
    def accept(seed, testdata, value):
        hasher = hashlib.md5()
        hasher.update(testdata.buffer)
        hasher.update(seed)
        return random.Random(hasher.digest()).random() <= p
    accept.__name__ = name or 'sometimes(%r)' % (p,)
    return accept


def array_average(seed, testdata, value):
    if np.prod(value.shape) == 0:
        return False
    avg = random.Random(seed).randint(0, 255)
    return value.mean() >= avg


def lower_bound(seed, testdata, value):
    """Benchmarking condition for testing the lexicographic minimization aspect
    of test case reduction.

    This lets us test for the sort of behaviour that happens when we
    e.g. have a lower bound on an integer, but in more generality.

    """

    # We implicitly define an infinite stream of bytes, and compare the buffer
    # of the testdata object with the prefix of the stream of the same length.
    # If it is >= that prefix we accept the testdata, if not we reject it.
    rnd = random.Random(seed)
    for b in testdata.buffer:
        c = rnd.randint(0, 255)
        if c < b:
            return True
        if c > b:
            return False
    return True


def size_lower_bound(seed, testdata, value):
    rnd = random.Random(seed)
    return len(testdata.buffer) >= rnd.randint(1, 50)


usually = sometimes(0.9, 'usually')


def minsum(seed, testdata, value):
    return sum(value) >= 1000


def has_duplicates(seed, testdata, value):
    return len(set(value)) < len(value)


for k in STRATEGIES:
    define_benchmark(k, always, never)
    define_benchmark(k, always, always)
    define_benchmark(k, always, usually)
    define_benchmark(k, always, lower_bound)

    define_benchmark(k, always, size_lower_bound)
    define_benchmark(k, usually, size_lower_bound)


define_benchmark('intlists', always, minsum)
define_benchmark('intlists', always, has_duplicates)
define_benchmark('intlists', has_duplicates, minsum)

for p in [always, usually]:
    define_benchmark('arrays10', p, array_average)
    define_benchmark('arraysvar', p, array_average)


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
    """This is a bootstrapped permutation test for the difference of means.

    Under the null hypothesis that the two sides come from the same
    distribution, we can randomly reassign values to different populations and
    see how large a difference in mean we get. This gives us a p-value for our
    actual observed difference in mean by counting the fraction of times our
    resampling got a value that large.

    See https://en.wikipedia.org/wiki/Resampling_(statistics)#Permutation_tests
    for details.

    """
    rnd = random.Random(0)

    threshold = abs(np.mean(existing) - np.mean(recent))
    n = len(existing)

    n_runs = 1000
    greater = 0

    all_values = existing + recent
    for _ in range(n_runs):
        rnd.shuffle(all_values)
        l = all_values[:n]
        r = all_values[n:]
        score = abs(np.mean(l) - np.mean(r))
        if score >= threshold:
            greater += 1
    return greater / n_runs


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
    return BenchmarkData(**parsed)


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
    sizes = new_data.sizes
    with open(benchmark_file(name), 'w') as o:
        o.write(BENCHMARK_HEADER % {
            'strategy_name': strategy_name,
            'strategy': benchmark.strategy,
            'valid': benchmark.valid.__name__,
            'interesting': benchmark.interesting.__name__,
            'seed': new_data.seed,
            'count': len(sizes),
            'min': min(sizes),
            'nmin': times(sizes.count(min(sizes))),
            'nmax': times(sizes.count(max(sizes))),
            'max': max(sizes),
            'mean': np.mean(sizes),
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
IMPROVED = 'improved'


@attr.s
class Report(object):
    name = attr.ib()
    p = attr.ib()
    old_mean = attr.ib()
    new_mean = attr.ib()
    new_data = attr.ib()
    new_seed = attr.ib()


def seed_by_int(i):
    # Get an actually good seed from an integer, as Random() doesn't guarantee
    # similar but distinct seeds giving different distributions.
    as_bytes = i.to_bytes(i.bit_length() // 8 + 1, 'big')
    digest = hashlib.sha1(as_bytes).digest()
    seedint = int.from_bytes(digest, 'big')
    random.seed(seedint)


@click.command()
@click.option(
    '--nruns', default=200, type=int, help="""
Specify the number of runs of each benchmark to perform. If this is larger than
the number of stored runs then this will result in the existing data treated as
if it were non-existing. If it is smaller, the existing data will be sampled.
""")
@click.argument('benchmarks', nargs=-1)
@click.option('--check/--no-check', default=False)
@click.option('--skip-existing/--no-skip-existing', default=False)
@click.option('--fdr', default=0.0001)
@click.option('--update', type=click.Choice([
    NONE, NEW, ALL, CHANGED, IMPROVED
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

    last_seed = 0
    for name in BENCHMARKS:
        if have_existing_data(name):
            last_seed = max(existing_data(name).seed, last_seed)

    next_seed = last_seed + 1

    reports = []
    if check:
        for name in benchmarks or BENCHMARKS:
            if not have_existing_data(name):
                click.echo('No existing data for benchmark %s' % (
                    name,
                ))
                sys.exit(1)

    for name in benchmarks or BENCHMARKS:
        new_seed = next_seed
        next_seed += 1
        seed_by_int(new_seed)
        if have_existing_data(name):
            if skip_existing:
                continue
            old_data = existing_data(name)
            new_data = run_benchmark_for_sizes(BENCHMARKS[name], nruns)

            pp = benchmark_difference_p_value(old_data.sizes, new_data)

            click.echo(
                '%r -> %r. p-value for difference %.5f' % (
                    np.mean(old_data.sizes), np.mean(new_data), pp,))
            reports.append(Report(
                name, pp, np.mean(old_data.sizes), np.mean(new_data), new_data,
                new_seed=new_seed,
            ))
            if update == ALL:
                write_data(name, BenchmarkData(sizes=new_data, seed=next_seed))
        elif update != NONE:
            new_data = run_benchmark_for_sizes(BENCHMARKS[name], nruns)
            write_data(name, BenchmarkData(sizes=new_data, seed=next_seed))

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
