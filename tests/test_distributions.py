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
import hypothesis.internal.distributions as dist
from hypothesis.errors import InvalidArgument


def test_non_empty_of_empty_errors():
    with pytest.raises(ValueError):
        dist.non_empty_subset(random, [])


def test_non_empty_of_one_always_returns_it():
    assert dist.non_empty_subset(random, [1]) == [1]
    assert dist.non_empty_subset(random, [2]) == [2]


def test_empty_dirichlet_is_invalid():
    with pytest.raises(InvalidArgument):
        dist.dirichlet(random, [])


def test_zeros_in_dirichlet_are_invalid():
    with pytest.raises(InvalidArgument):
        dist.dirichlet(random, [0.0, 1.0])


def test_dirichlet_biases_towaards_weights():
    t = dist.dirichlet(random, [10000000000, 1, 1])
    assert t[0] >= 0.8
