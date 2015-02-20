# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import random

import pytest
import hypothesis.settings as hs
from hypothesis.database import ExampleDatabase
from hypothesis.examplesource import ExampleSource
from hypothesis.strategytable import StrategyTable
from hypothesis.internal.compat import hrange

N_EXAMPLES = 1000


def test_negative_is_not_too_far_off_mean():
    source = ExampleSource(
        random=random.Random(),
        strategy=StrategyTable.default().strategy(int),
        storage=None,
    )
    positive = 0
    i = 0
    for example in source:
        if example >= 0:
            positive += 1
        i += 1
        if i >= N_EXAMPLES:
            break
    assert 0.3 <= float(positive) / N_EXAMPLES <= 0.7


def test_marking_negative_avoids_similar_examples():
    source = ExampleSource(
        random=random.Random(),
        strategy=StrategyTable.default().strategy(int),
        storage=None,
    )
    positive = 0
    i = 0
    for example in source:
        if example >= 0:
            positive += 1
        else:
            source.mark_bad()
        i += 1
        if i >= N_EXAMPLES:
            break
    assert float(positive) / N_EXAMPLES >= 0.8


def test_can_grow_the_set_of_available_parameters_if_doing_badly():
    runs = 10
    number_grown = 0
    for _ in hrange(runs):
        source = ExampleSource(
            random=random.Random(),
            strategy=StrategyTable.default().strategy(int),
            storage=None,
            min_parameters=1,
        )
        i = 0
        for example in source:
            if example < 0:
                source.mark_bad()
            i += 1
            if i >= 100:
                break
        if len(source.parameters) > 1:
            number_grown += 1
        assert len(source.parameters) < 100


def test_example_source_needs_at_least_one_useful_argument():
    with pytest.raises(ValueError):
        ExampleSource(random=random.Random(), storage=None, strategy=None)


def test_example_source_needs_random():
    with pytest.raises(ValueError):
        ExampleSource(
            random=None,
            strategy=StrategyTable.default().strategy(int),
            storage=None,
        )


def test_example_source_terminates_if_just_from_db():
    db = ExampleDatabase()
    storage = db.storage_for(int)
    storage.save(1)
    source = ExampleSource(
        random=random.Random(), storage=storage, strategy=None)
    its = iter(source)
    assert next(its) == 1
    with pytest.raises(StopIteration):
        next(its)


def test_errors_if_you_mark_bad_twice():
    storage = None
    if hs.default.database is not None:
        storage = hs.default.database.storage_for(int)
    source = ExampleSource(
        random=random.Random(),
        strategy=StrategyTable.default().strategy(int),
        storage=storage,
    )
    next(iter(source))
    source.mark_bad()
    with pytest.raises(ValueError):
        source.mark_bad()


def test_errors_if_you_mark_bad_before_fetching():
    storage = None
    if hs.default.database is not None:
        storage = hs.default.database.storage_for(int)
    source = ExampleSource(
        random=random.Random(),
        strategy=StrategyTable.default().strategy(int),
        storage=storage,
    )
    with pytest.raises(ValueError):
        source.mark_bad()


def test_tries_each_parameter_at_least_min_index_times():
    source = ExampleSource(
        random=random.Random(),
        strategy=StrategyTable.default().strategy(int),
        storage=None,
        min_tries=5
    )
    i = 0
    for x in source:
        i += 1
        if i > 500:
            break
        if i % 2:
            source.mark_bad()
    # The last index may not have been fully populated
    assert all(c >= 5 for c in source.counts[:-1])
