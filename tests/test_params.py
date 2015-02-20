# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pytest
import hypothesis.params as params


def test_non_empty_subset_on_one_element_does_not_call_random():
    x = params.NonEmptySubset([1])
    x.draw('this is bogus')


def test_non_empty_subset_errors_on_empty_set():
    with pytest.raises(ValueError) as e:
        params.NonEmptySubset([])
    assert 'at least one' in e.value.args[0]


def test_biased_coin_only_accepts_proper_probabilities():
    for bad in [-1.0, 0, 1.0, 10e6]:
        with pytest.raises(ValueError):
            params.BiasedCoin(bad)


def test_exponential_errors_on_negative_mean():
    with pytest.raises(ValueError):
        params.ExponentialParameter(-1)


def test_composite_parameter_name_clashes():
    with pytest.raises(ValueError) as e:
        params.CompositeParameter(
            params.BiasedCoin(0.5),
            arg0=params.BiasedCoin(0.5),
        )
    assert 'duplicate' in e.value.args[0].lower()
    with pytest.raises(ValueError) as e:
        params.CompositeParameter(
            __init__=params.BiasedCoin(0.5),
        )
    assert 'invalid' in e.value.args[0].lower()
