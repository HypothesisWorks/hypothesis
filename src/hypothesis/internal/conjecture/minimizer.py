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

from hypothesis.internal.compat import hbytes, hrange


"""
This module implements a lexicographic minimizer for blocks of bytearray.

That is, given a block of bytes of size n, and a predicate that accepts such
blocks, it tries to find a lexicographically minimal block of that size
that satisifies the predicate, starting from that initial starting point.

Assuming it is allowed to run to completion (which due to the way we use it it
actually often isn't) it makes the following guarantees, but it usually tries
to do better in practice:

1. The lexicographic predecessor (i.e. the largest block smaller than it) of
   the answer is not a solution.
2. No individual byte in the solution may be lowered while holding the others
   fixed.
"""


class Minimizer(object):

    def __init__(self, initial, condition, random):
        self.current = hbytes(initial)
        self.size = len(self.current)
        self.condition = condition
        self.random = random
        self.changes = 0

    def incorporate(self, buffer):
        assert isinstance(buffer, hbytes)
        assert len(buffer) == self.size
        assert buffer <= self.current
        if self.condition(buffer):
            self.current = buffer
            self.changes += 1
            return True
        return False

    def _shrink_index(self, i, c):
        assert isinstance(self.current, hbytes)
        assert 0 <= i < self.size
        if self.current[i] <= c:
            return False
        if self.incorporate(
            self.current[:i] + hbytes([c]) +
            self.current[i + 1:]
        ):
            return True
        if i == self.size - 1:
            return False
        return self.incorporate(
            self.current[:i] + hbytes([c, 255]) +
            self.current[i + 2:]
        ) or self.incorporate(
            self.current[:i] + hbytes([c]) +
            hbytes([255] * (self.size - i - 1))
        )

    def run(self):
        if not any(self.current):
            return
        if self.incorporate(hbytes(self.size)):
            return
        for c in hrange(max(self.current)):
            if self.incorporate(
                hbytes(min(b, c) for b in self.current)
            ):
                break

        change_counter = -1
        while self.current and change_counter < self.changes:
            change_counter = self.changes
            for i in hrange(self.size):
                t = self.current[i]
                if t > 0:
                    ss = small_shrinks[self.current[i]]
                    for c in ss:
                        if self._shrink_index(i, c):
                            for c in hrange(self.current[i]):
                                if c in ss:
                                    continue
                                if self._shrink_index(i, c):
                                    break
                            break


# Table of useful small shrinks to apply to a number.
# The idea is that we use these first to see if shrinking is likely to work.
# If it is, we try a full shrink. In the best case scenario this speeds us
# up by a factor of about 25. It will occasonally cause us to miss
# shrinks that we could have succeeded with, but oh well. It doesn't fail any
# of our guarantees because we do try to shrink to -1 among other things.
small_shrinks = [
    set(range(b)) for b in hrange(10)
]

for b in hrange(10, 256):
    result = set()
    result.add(0)
    result.add(b - 1)
    for i in hrange(8):
        result.add(b ^ (1 << i))
    result.discard(b)
    assert len(result) <= 10
    small_shrinks.append(sorted(result))


def minimize(initial, condition, random=None):
    m = Minimizer(initial, condition, random)
    m.run()
    return m.current
