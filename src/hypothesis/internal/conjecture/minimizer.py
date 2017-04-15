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

from hypothesis.internal.compat import hbytes, hrange


"""
This module implements a lexicographic minimizer for blocks of bytearray.

That is, given a block of bytes of size n, and a predicate that accepts such
blocks, it tries to find a lexicographically minimal block of that size
that satisfies the predicate, starting from that initial starting point.

Assuming it is allowed to run to completion (which due to the way we use it it
actually often isn't) it makes the following guarantees, but it usually tries
to do better in practice:

1. The lexicographic predecessor (i.e. the largest block smaller than it) of
   the answer is not a solution.
2. No individual byte in the solution may be lowered while holding the others
   fixed.
"""


class Minimizer(object):

    def __init__(self, initial, condition, random, cautious):
        self.current = hbytes(initial)
        self.size = len(self.current)
        self.condition = condition
        self.random = random
        self.cautious = cautious
        self.changes = 0
        self.seen = set()

    def incorporate(self, buffer):
        assert isinstance(buffer, hbytes)
        assert len(buffer) == self.size
        assert buffer <= self.current
        if buffer in self.seen:
            return False
        self.seen.add(buffer)
        if buffer != self.current and self.condition(buffer):
            self.current = buffer
            self.changes += 1
            return True
        return False

    def _shrink_index(self, i, c):
        assert isinstance(self.current, hbytes)
        assert 0 <= i < self.size
        assert self.current[i] > c
        if self.incorporate(
            self.current[:i] + hbytes([c]) +
            self.current[i + 1:]
        ):
            return True

        if self.cautious:
            return False

        if i == self.size - 1:
            return False

        return self.incorporate(
            self.current[:i] + hbytes([c, 255]) +
            self.current[i + 2:]
        ) or self.incorporate(
            self.current[:i] + hbytes([c]) +
            hbytes([255] * (self.size - i - 1))
        )

    def ddzero(self):
        self.ddfixate(lambda b: 0)

    def ddshift(self):
        self.ddfixate(lambda b: b >> 1)

    def ddfixate(self, f):
        prev = -1
        while prev != self.changes:
            prev = self.changes
            k = len(self.current)
            while k > 0:
                i = 0
                while i + k <= len(self.current):
                    self.incorporate(
                        self.current[:i] +
                        hbytes(f(b) for b in self.current[i:i + k]) +
                        self.current[i + k:]
                    )
                    i += k
                k //= 2

    def rotate_suffixes(self):
        for significant, c in enumerate(self.current):  # pragma: no branch
            if c:
                break
        assert self.current[significant]

        prefix = hbytes(significant)

        for i in range(1, self.size - significant):
            left = self.current[significant:significant + i]
            right = self.current[significant + i:]
            rotated = prefix + right + left
            if rotated < self.current:
                self.incorporate(rotated)

    def shrink_indices(self):
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

    def run(self):
        if not any(self.current):
            return
        if len(self.current) == 1:
            for c in range(self.current[0]):
                if self.incorporate(hbytes([c])):
                    break
            return
        if self.incorporate(hbytes(self.size)):
            return
        if self.incorporate(hbytes([0] * (self.size - 1) + [1])):
            return
        change_counter = -1
        while self.current and change_counter < self.changes:
            change_counter = self.changes

            self.ddzero()
            self.ddshift()

            if change_counter != self.changes:
                continue

            self.shrink_indices()

            if change_counter != self.changes or self.cautious:
                continue

            self.rotate_suffixes()


# Table of useful small shrinks to apply to a number.
# The idea is that we use these first to see if shrinking is likely to work.
# If it is, we try a full shrink. In the best case scenario this speeds us
# up by a factor of about 25. It will occasionally cause us to miss
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
    small_shrinks.append(sorted([c for c in result if c < b]))


def minimize(initial, condition, random=None, cautious=False):
    """Perform a lexicographical minimization of the byte string 'initial' such
    that the predicate 'condition' returns True, and return the minimized
    string.

    If 'cautious' is set to True, this will only consider strings that
    satisfy the stronger condition that no individual byte is increased
    from the original. e.g. normally bytes([0, 255]) is considered a
    valid shrink of bytes([1, 0]), but if cautious is set it will not
    be.

    """
    m = Minimizer(initial, condition, random, cautious)
    m.run()
    return m.current
