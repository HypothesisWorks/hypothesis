# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

from random import Random

import pytest

import hypothesis.internal.conjecture.utils as cu
from hypothesis import HealthCheck, settings
from hypothesis.internal.compat import hbytes, hrange
from hypothesis.internal.conjecture.engine import (
    ConjectureData,
    ConjectureRunner,
    uniform,
)
from hypothesis.searchstrategy import SearchStrategy

POISON = "POISON"

MAX_INT = 2 ** 32 - 1


class PoisonedTree(SearchStrategy):
    """Generates variable sized tuples with an implicit tree structure.

    The actual result is flattened out, but the hierarchy is implicit in
    the data.
    """

    def __init__(self, p):
        SearchStrategy.__init__(self)
        self.__p = p

    def do_draw(self, data):
        if cu.biased_coin(data, self.__p):
            return data.draw(self) + data.draw(self)
        else:
            # We draw n as two separate calls so that it doesn't show up as a
            # single block. If it did, the heuristics that allow us to move
            # blocks around would fire and it would move right, which would
            # then allow us to shrink it more easily.
            n = (data.draw_bits(16) << 16) | data.draw_bits(16)
            if n == MAX_INT:
                return (POISON,)
            else:
                return (None,)


LOTS = 10 ** 6


TEST_SETTINGS = settings(
    database=None,
    suppress_health_check=HealthCheck.all(),
    max_examples=LOTS,
    deadline=None,
)


@pytest.mark.parametrize("size", [2, 5, 10])
@pytest.mark.parametrize("seed", [0, 15993493061449915028])
def test_can_reduce_poison_from_any_subtree(size, seed):
    """This test validates that we can minimize to any leaf node of a binary
    tree, regardless of where in the tree the leaf is."""
    random = Random(seed)

    # Initially we create the minimal tree of size n, regardless of whether it
    # is poisoned (which it won't be - the poison event essentially never
    # happens when drawing uniformly at random).

    # Choose p so that the expected size of the tree is equal to the desired
    # size.
    p = 1.0 / (2.0 - 1.0 / size)
    strat = PoisonedTree(p)

    def test_function(data):
        v = data.draw(strat)
        if len(v) >= size:
            data.mark_interesting()

    runner = ConjectureRunner(test_function, random=random, settings=TEST_SETTINGS)

    while not runner.interesting_examples:
        runner.test_function(
            runner.new_conjecture_data(lambda data, n: uniform(random, n))
        )

    runner.shrink_interesting_examples()

    (data,) = runner.interesting_examples.values()

    assert len(ConjectureData.for_buffer(data.buffer).draw(strat)) == size

    starts = [b.start for b in data.blocks if b.length == 2]
    assert len(starts) % 2 == 0

    for i in hrange(0, len(starts), 2):
        # Now for each leaf position in the tree we try inserting a poison
        # value artificially. Additionally, we add a marker to the end that
        # must be preserved. The marker means that we are not allow to rely on
        # discarding the end of the buffer to get the desired shrink.
        u = starts[i]
        marker = hbytes([1, 2, 3, 4])

        def test_function_with_poison(data):
            v = data.draw(strat)
            m = data.draw_bytes(len(marker))
            if POISON in v and m == marker:
                data.mark_interesting()

        runner = ConjectureRunner(
            test_function_with_poison, random=random, settings=TEST_SETTINGS
        )

        runner.cached_test_function(
            data.buffer[:u] + hbytes([255]) * 4 + data.buffer[u + 4 :] + marker
        )

        assert runner.interesting_examples
        runner.shrink_interesting_examples()

        (shrunk,) = runner.interesting_examples.values()

        assert ConjectureData.for_buffer(shrunk.buffer).draw(strat) == (POISON,)
