# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

from hypothesis.internal.conjecture.shrinking.common import Shrinker, \
    find_integer


def identity(v):
    return v


class Ordering(Shrinker):
    """A shrinker that tries to make a sequence more sorted.

    Will not change the length or the contents, only tries to reorder
    the elements of the sequence.
    """

    def __init__(self, initial, predicate, random, full, key=identity):
        super(Ordering, self).__init__(initial, predicate, random, full)
        self.key = key

    def make_immutable(self, value):
        return tuple(value)

    def short_circuit(self):
        # If we can flat out sort the target then there's nothing more to do.
        return self.consider(sorted(self.current, key=self.key))

    def left_is_better(self, left, right):
        return tuple(map(self.key, left)) < tuple(map(self.key, right))

    def check_invariants(self, value):
        assert len(value) == len(self.current)
        assert sorted(value) == sorted(self.current)

    def run_step(self):
        for i in range(len(self.current)):
            # This is essentially insertion sort, but unlike normal insertion
            # sort because of our use of find_integer we only perform
            # O(n(log(n))) calls. Because of the rotations we're still O(n^2)
            # performance in terms of number of list operations, but we don't
            # care about those so much.
            original = self.current

            def push_back(k):
                if k > i:
                    return False
                j = i - k
                attempt = list(original)
                del attempt[i]
                attempt.insert(j, original[i])
                return self.consider(attempt)

            find_integer(push_back)
