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

import math


def uniform_float(random, start, end):
    return start + random.random() * (end - start)


def geometric(random, p):
    """Generate a geometric integer in the range [0, infinity) with expected
    value.

    1 / p - 1

    """
    denom = math.log1p(-p)
    return int(math.log(random.random()) / denom)


def biased_coin(random, p):
    return random.random() <= p


def non_empty_subset(random, elements, activation_chance=None):
    elements = tuple(elements)
    if not elements:
        raise ValueError(u'Must have at least one element')
    if len(elements) == 1:
        return list(elements)
    if activation_chance is None:
        # TODO: This should have a more principled choice. It seems to be
        # good in practice though.
        # Note: The actual expected value is slightly higher because we're
        # conditioning on the result being non-empty.
        if len(elements) <= 3:
            desired_expected_value = 1.75
        else:
            desired_expected_value = 2.0
        activation_chance = desired_expected_value / len(elements)

    result = []
    while not result:
        result = [
            x
            for x in elements
            if biased_coin(random, activation_chance)
        ]
    return result
