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

from hypothesis.errors import InvalidArgument
from hypothesis.internal.compat import hrange


class chooser(object):

    def __init__(self, weights):
        weights = list(weights)
        if not weights:
            raise InvalidArgument(
                u'Must have at least one element to choose from')
        for w in weights:
            if w < 0:
                raise InvalidArgument(
                    u'Invalid weight %f < 0' % (w,)
                )
        normalizer = max(weights)
        if normalizer <= 0:
            raise InvalidArgument(u'No non-zero weights in %r' % (weights,))
        for i in hrange(len(weights)):
            weights[i] /= normalizer
        self.weights = tuple(weights)

    def choose(self, random):
        while True:
            i = random.randint(0, len(self.weights) - 1)
            if random.random() <= self.weights[i]:
                return i
