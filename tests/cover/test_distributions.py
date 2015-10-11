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

import pytest

import hypothesis.internal.distributions as dist


def test_non_empty_of_empty_errors():
    with pytest.raises(ValueError):
        dist.non_empty_subset(random, [])


def test_non_empty_of_one_always_returns_it():
    assert dist.non_empty_subset(random, [1]) == [1]
    assert dist.non_empty_subset(random, [2]) == [2]


def test_non_empty_of_three():
    assert dist.non_empty_subset(random, [1, 2, 3])


def test_non_empty_of_10():
    assert dist.non_empty_subset(random, range(10))


def test_non_empty_with_explicit_activation_chance():
    assert len(dist.non_empty_subset(
        random, range(100), activation_chance=0.99)) > 2
