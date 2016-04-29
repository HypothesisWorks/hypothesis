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

import pytest

from hypothesis import find, given
from hypothesis.internal.compat import int_to_bytes
from hypothesis.searchstrategy.fixed import FixedStrategy


class Blocks(FixedStrategy):

    def draw_value(self, random):
        return int_to_bytes(
            random.getrandbits(self.block_size * 8), self.block_size)

    def to_bytes(self, value):
        return value

    def from_bytes(self, value):
        return value


@given(Blocks(3))
def test_blocks_are_of_fixed_size(x):
    assert len(x) == 3


def test_blocks_shrink_bytewise():
    assert find(Blocks(5), lambda x: True) == b'\0' * 5


class BadBlocks(Blocks):

    def is_acceptable(self, value):
        return False


def test_bad_blocks_error():
    with pytest.raises(AssertionError):
        find(BadBlocks(5), lambda x: True)


class BadlySizedBlocks(Blocks):

    def to_bytes(self, value):
        return value + b'\0'


def test_badly_sized_blocks_error():
    with pytest.raises(AssertionError):
        find(BadlySizedBlocks(5), lambda x: True)


class FilteredBlocks(Blocks):

    def is_acceptable(self, value):
        return value[-1] & 1


@given(FilteredBlocks(3))
def test_filtered_blocks_are_acceptable(x):
    assert len(x) == 3
    assert x[-1] & 1
