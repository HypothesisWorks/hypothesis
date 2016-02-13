# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import os
import hypothesis.strategies as st
from hypothesis import find, settings

settings.register_profile('benchmarking', settings(
    database=None,
))


import pytest
import random


def setup_module():
    settings.load_profile('benchmarking')


def teardown_module():
    settings.load_profile(os.getenv('HYPOTHESIS_PROFILE', 'default'))


strategies = [
    st.integers(),
    st.text(),
    st.binary(),
    st.floats(),
    st.integers().flatmap(lambda x: st.lists(st.integers(max_value=x)))
]

strategies.extend(list(map(st.lists, strategies)))

# Nothing special, just want a fixed seed list.
seeds = [
    17449917217797177955,
    10900658426497387440,
    3678508287585343099,
    11902419052042326073,
    8648395390016624135
]


bench = pytest.mark.parametrize(
    ('strategy', 'seed'), [
        (strat, seed) for strat in strategies for seed in seeds
    ],
    ids=[
        '%r-%d' % (strat, seed) for strat in strategies for seed in seeds
    ]
)


@bench
def test_one_off_generation(benchmark, strategy, seed):
    @benchmark
    def run():
        strategy.example(random.Random(seed))


@bench
def test_minimize_to_minimal(benchmark, strategy, seed):
    @benchmark
    def run():
        find(strategy, lambda x: True, random=random.Random(seed))


@bench
def test_minimize_to_not_minimal(benchmark, strategy, seed):
    @benchmark
    def run():
        rnd = random.Random(seed)
        minimal = find(strategy, lambda x: True, random=rnd)
        find(strategy, lambda x: x != minimal, random=rnd)


@bench
def test_total_failure_to_minimize(benchmark, strategy, seed):
    @benchmark
    def run():
        rnd = random.Random(seed)
        ex = []

        def is_first(x):
            if ex:
                return x == ex[0]
            else:
                ex.append(x)
                return True
        find(strategy, lambda x: True, random=rnd)
