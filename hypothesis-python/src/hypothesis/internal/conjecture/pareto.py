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

from enum import Enum

from hypothesis.internal.conjecture.data import ConjectureData, ConjectureResult, Status
from hypothesis.internal.conjecture.shrinker import sort_key


class DominanceRelation(Enum):
    NO_DOMINANCE = 0
    EQUAL = 1
    LEFT_DOMINATES = 2
    RIGHT_DOMINATES = 3


def dominance(left, right):
    """Returns the dominance relation between ``left`` and ``right``, according
    to the rules that something dominates if and only if it is better in every
    way.

    The things we currently consider to be "better" are:

        * Something that is smaller in shrinking order is better.
        * Something that has higher status is better.
        * Each ``interesting_origin`` is treated as its own score, so if two
          interesting examples have different origins then neither dominates
          the other.
        * For each target observation, a higher score is better.

    In "normal" operation where there are no bugs or target observations, the
    pareto front only has one element (the smallest valid test case), but for
    more structured or failing tests it can be useful to track, and future work
    will depend on it more."""

    if left.buffer == right.buffer:
        return DominanceRelation.EQUAL

    if sort_key(right.buffer) < sort_key(left.buffer):
        result = dominance(right, left)
        if result == DominanceRelation.LEFT_DOMINATES:
            return DominanceRelation.RIGHT_DOMINATES
        else:
            # Because we have sort_key(left) < sort_key(right) the only options
            # are that right is better than left or that the two are
            # incomparable.
            assert result == DominanceRelation.NO_DOMINANCE
            return result

    # Either left is better or there is no dominance relationship.
    assert sort_key(left.buffer) < sort_key(right.buffer)

    # The right is more interesting
    if left.status < right.status:
        return DominanceRelation.NO_DOMINANCE

    # Things that are interesting for different reasons are incomparable in
    # the dominance relationship.
    if (
        left.status == Status.INTERESTING
        and left.interesting_origin != right.interesting_origin
    ):
        return DominanceRelation.NO_DOMINANCE

    for target, score in left.target_observations.items():
        if (
            target in right.target_observations
            and right.target_observations[target] > score
        ):
            return DominanceRelation.NO_DOMINANCE

    return DominanceRelation.LEFT_DOMINATES


class ParetoFront(object):
    """Maintains an approximate pareto front of ConjectureData objects. That
    is, we try to maintain a collection of objects such that no element of the
    collection is pareto dominated by any other. In practice we don't quite
    manage that, because doing so is computationally very expensive. Instead
    we maintain a random sample of data objects that are "rarely" dominated by
    any other element of the collection (roughly, no more than about 10%).

    Only valid test cases are considered to belong to the pareto front - any
    test case with a status less than valid is discarded.
    """

    def __init__(self, random):
        self.__random = random
        self.__eviction_listeners = []

        self.__front = []
        self.__contained = {}
        self.__pending = None

    def add(self, data):
        """Attempts to add ``data`` to the pareto front. Returns True if this
        resulted ``data`` being added, otherwise returns False (including if
        data is already in the collection)."""
        if data.status < Status.VALID:
            return False

        if not self.__front:
            self.__add(data)
            return True

        if data.buffer in self.__contained:
            return False

        # We add data to the pareto front by adding it unconditionally and then
        # doing a certain amount of randomized "clear down" - testing a random
        # set of elements (currently 10) to see if they are dominated by
        # something else in the collection. If they are, we remove them.
        self.__add(data)
        assert self.__pending is None
        try:
            self.__pending = data

            best = data

            i = len(self.__front) - 1
            stopping = max(0, len(self.__front) - 10)
            while i >= stopping:
                self.__swap(i, self.__random.randint(0, i))

                existing = self.__front[i]
                dom = dominance(existing, best)
                if dom == DominanceRelation.LEFT_DOMINATES:
                    self.__remove(best)
                    best = existing
                elif dom == DominanceRelation.RIGHT_DOMINATES:
                    self.__remove(existing)
                i -= 1
            return data.buffer in self.__contained
        finally:
            self.__pending = None

    def on_evict(self, f):
        """Register a listener function that will be called with data when it
        gets removed from the front because something else dominates it."""
        self.__eviction_listeners.append(f)

    def __contains__(self, data):
        return isinstance(data, (ConjectureData, ConjectureResult)) and (
            data.buffer in self.__contained
        )

    def __iter__(self):
        return iter(self.__front)

    def __len__(self):
        return len(self.__front)

    def __add(self, data):
        assert data.buffer not in self.__contained
        i = len(self.__front)
        self.__front.append(data)
        self.__contained[data.buffer] = i

    def __remove(self, data):
        i = self.__contained[data.buffer]
        self.__swap(i, len(self.__front) - 1)
        self.__front.pop()
        self.__contained.pop(data.buffer)
        if data is not self.__pending:
            for f in self.__eviction_listeners:
                f(data)

    def __swap(self, i, j):
        if i == j:
            return
        self.__front[i], self.__front[j] = self.__front[j], self.__front[i]
        for k in (i, j):
            self.__contained[self.__front[k].buffer] = k
