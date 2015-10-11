# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

import random
from itertools import islice

import pytest

from hypothesis.strategies import integers
from hypothesis.internal.compat import hrange
from hypothesis.internal.examplesource import ParameterSource

N_EXAMPLES = 25000


def test_can_use_none_max_tries():
    source = ParameterSource(
        random=random.Random(),
        strategy=integers(),
        max_tries=None,
    )
    source.pick_a_parameter()


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
