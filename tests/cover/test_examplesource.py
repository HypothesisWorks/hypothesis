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
from itertools import islice

import pytest
from hypothesis.strategies import booleans, integers
from hypothesis.internal.compat import hrange
from hypothesis.internal.examplesource import ParameterSource

N_EXAMPLES = 2500


def test_negative_is_not_too_far_off_mean():
    source = ParameterSource(
        random=random.Random(),
        strategy=integers(),
    )
    positive = 0
    i = 0
    for example in source.examples():
        if example >= 0:
            positive += 1
        i += 1
        if i >= N_EXAMPLES:
            break
    assert 0.3 <= float(positive) / N_EXAMPLES <= 0.7


def test_marking_negative_avoids_similar_examples():
    positive = 0
    k = 10

    for _ in hrange(k):
        source = ParameterSource(
            random=random.Random(),
            strategy=integers(),
        )
        n = N_EXAMPLES // k
        for example in islice(source.examples(), n):
            if example >= 0:
                positive += 1
            else:
                source.mark_bad()
    assert float(positive) / N_EXAMPLES >= 0.7


def test_can_grow_the_set_of_available_parameters_if_doing_badly():
    runs = 10
    number_grown = 0
    for _ in hrange(runs):
        source = ParameterSource(
            random=random.Random(),
            strategy=integers(),
            min_parameters=1,
        )
        i = 0
        for example in source.examples():
            if example < 0:
                source.mark_bad()
            i += 1
            if i >= 100:
                break
        if len(source.parameters) > 1:
            number_grown += 1
        assert len(source.parameters) < 100


def test_errors_if_you_mark_bad_twice():
    source = ParameterSource(
        random=random.Random(),
        strategy=integers(),
    )
    next(iter(source))
    source.mark_bad()
    with pytest.raises(ValueError):
        source.mark_bad()


def test_errors_if_you_mark_bad_before_fetching():
    source = ParameterSource(
        random=random.Random(),
        strategy=integers(),
    )
    with pytest.raises(ValueError):
        source.mark_bad()


def test_tries_each_parameter_at_least_min_index_times():
    source = ParameterSource(
        random=random.Random(),
        strategy=integers(),
        min_tries=5
    )
    i = 0
    for x in source.examples():
        i += 1
        if i > 500:
            break
        if i % 2:
            source.mark_bad()
    # The last index may not have been fully populated
    assert all(c >= 5 for c in source.counts[:-1])


def test_culls_valid_parameters_if_lots_are_bad():
    source = ParameterSource(
        random=random.Random(),
        strategy=integers(),
        min_tries=5
    )
    for _ in islice(source, 200):
        source.mark_bad()

    for i in hrange(len(source.parameters)):
        assert source.counts[i] >= source.bad_counts[i]

    for i in hrange(len(source.parameters)):
        assert source.counts[i] == source.bad_counts[i]

    assert len(source.valid_parameters) <= 1


def test_caps_number_of_parameters_tried():
    source = ParameterSource(
        random=random.Random(),
        strategy=booleans(),
        max_tries=1,
    )

    for p in islice(source, 200):
        pass

    assert all(t <= 1 for t in source.counts)


def test_eventually_culls_parameters_which_stop_being_valid():
    source = ParameterSource(
        random=random.Random(),
        strategy=booleans(),
        min_tries=5
    )
    seen = set()
    for p in islice(source, 200):
        if p in seen:
            source.mark_bad()
        else:
            seen.add(p)

    for i in hrange(len(source.parameters)):
        assert source.counts[i] >= source.bad_counts[i]

    for i in hrange(len(source.parameters)):
        assert source.counts[i] == source.bad_counts[i] + 1

    assert len(source.valid_parameters) <= len(source.parameters) // 2
