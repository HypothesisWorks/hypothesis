# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from random import Random

import pytest

from hypothesis import HealthCheck, settings
from hypothesis.internal.conjecture.engine import ConjectureData, ConjectureRunner
from hypothesis.strategies._internal import SearchStrategy

POISON = "POISON"
MAX_INT = 2**32 - 1


class PoisonedTree(SearchStrategy):
    """Generates variable sized tuples with an implicit tree structure.

    The actual result is flattened out, but the hierarchy is implicit in
    the data.
    """

    def __init__(self, p):
        super().__init__()
        self.__p = p

    def do_draw(self, data):
        if data.draw_boolean(self.__p):
            return data.draw(self) + data.draw(self)
        else:
            # We draw n as two separate calls so that it doesn't show up as a
            # single block. If it did, the heuristics that allow us to move
            # blocks around would fire and it would move right, which would
            # then allow us to shrink it more easily.
            n1 = data.draw_integer(0, 2**16 - 1) << 16
            n2 = data.draw_integer(0, 2**16 - 1)
            n = n1 | n2
            if n == MAX_INT:
                return (POISON,)
            else:
                return (None,)


TEST_SETTINGS = settings(
    database=None,
    suppress_health_check=list(HealthCheck),
    max_examples=10**6,
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
    runner.generate_new_examples()
    runner.shrink_interesting_examples()
    (data,) = runner.interesting_examples.values()
    assert len(ConjectureData.for_choices(data.choices).draw(strat)) == size

    # find the nodes corresponding to n1 and n2
    nodes = [
        node
        for node in data.nodes
        if node.type == "integer" and node.kwargs["max_value"] == 2**16 - 1
    ]
    assert len(nodes) % 2 == 0

    marker = bytes([1, 2, 3, 4])
    for i in range(0, len(nodes), 2):
        # Now for each leaf position in the tree we try inserting a poison
        # value artificially. Additionally, we add a marker to the end that
        # must be preserved. The marker means that we are not allow to rely on
        # discarding the end of the choice sequence to get the desired shrink.
        node = nodes[i]

        def test_function_with_poison(data):
            v = data.draw(strat)
            m = data.draw_bytes(len(marker), len(marker))
            if POISON in v and m == marker:
                data.mark_interesting()

        runner = ConjectureRunner(
            test_function_with_poison, random=random, settings=TEST_SETTINGS
        )
        # replace n1 and n2 with 2**16 - 1 to insert a poison value here
        runner.cached_test_function_ir(
            data.choices[: node.index]
            + (2**16 - 1, 2**16 - 1)
            + (data.choices[node.index + 2 :])
            + (marker,)
        )
        assert runner.interesting_examples

        runner.shrink_interesting_examples()
        (shrunk,) = runner.interesting_examples.values()
        assert ConjectureData.for_choices(shrunk.choices).draw(strat) == (POISON,)
