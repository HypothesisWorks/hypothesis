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

from __future__ import division, print_function, absolute_import


class KahanSummation(object):
    """Incremental implementation of Kahan Summation.

    Maintains a more accurate running sum of a series of values than we would
    get by just repeatedly doing += on a counter.

    See https://en.wikipedia.org/wiki/Kahan_summation_algorithm for details.

    """

    def __init__(self):
        self.sum = 0.0
        self.carry = 0.0

    def add(self, value):
        # Incorporate the leftover from the previous summation
        value += self.carry

        previous_sum = self.sum

        self.sum += value

        # Replace the carry with the difference between where we've ended up
        # and where we "should" be.
        self.carry = (self.sum - previous_sum) - value
