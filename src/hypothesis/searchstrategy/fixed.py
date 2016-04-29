# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

from hypothesis.control import assume
from hypothesis.searchstrategy.strategies import SearchStrategy


class FixedStrategy(SearchStrategy):

    def __init__(self, block_size):
        self.block_size = block_size

    def do_draw(self, data):
        block = data.draw_bytes(self.block_size, self.distribution)
        assert len(block) == self.block_size
        value = self.from_bytes(block)
        assume(self.is_acceptable(value))
        return value

    def distribution(self, random, n):
        assert n == self.block_size
        for _ in range(100):
            value = self.draw_value(random)
            if self.is_acceptable(value):
                block = self.to_bytes(value)
                assert len(block) == self.block_size
                return block
        raise AssertionError(
            'After 100 tries was unable to draw a valid value. This is a bug '
            'in the implementation of %s.' % (type(self).__name__,))

    def draw_value(self, random):
        raise NotImplementedError('%s.draw' % (
            type(self).__name__,
        ))

    def to_bytes(self, value):
        raise NotImplementedError('%s.to_bytes' % (
            type(self).__name__,
        ))

    def from_bytes(self, value):
        raise NotImplementedError('%s.from_bytes' % (
            type(self).__name__,
        ))

    def is_acceptable(self, value):
        return True
