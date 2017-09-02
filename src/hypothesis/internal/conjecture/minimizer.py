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
This module implements a lexicographic minimizer for blocks of bytes.

That is, given a block of bytes of a given size, and a predicate that accepts
such blocks, it tries to find a lexicographically minimal block of that size
that satisfies the predicate, by repeatedly making local changes to that
starting point.

Assuming it is allowed to run to completion (which due to the way we use it it
actually often isn't) it makes the following guarantees, but it usually tries
to do better in practice:

1. The lexicographic predecessor (i.e. the largest block smaller than it) of
   the answer is not a solution.
2. No individual byte in the solution may be lowered while holding the others
   fixed.
"""


class Minimizer(object):

    def __init__(self, initial, condition, random, full):
        self.current = hbytes(initial)
        self.size = len(self.current)
        self.condition = condition
        self.random = random
        self.full = full
        self.changes = 0
        self.seen = set()

    def incorporate(self, buffer):
        """Consider this buffer as a possible replacement for the current best
        buffer.

        Return True if it succeeds as such.

        """
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

    def shift(self):
        """Attempt to shift individual byte values right as far as they can
        go."""
        prev = -1
        while prev != self.changes:
            prev = self.changes
            for i in hrange(self.size):
                block = bytearray(self.current)
                c = block[i]
                for k in hrange(c.bit_length(), 0, -1):
                    block[i] = c >> k
                    if self.incorporate(hbytes(block)):
                        break

    def rotate_suffixes(self):
        for significant, c in enumerate(self.current):  # pragma: no branch
            if c:
                break
        assert self.current[significant]

        prefix = hbytes(significant)

        for i in hrange(1, self.size - significant):
            left = self.current[significant:significant + i]
            right = self.current[significant + i:]
            rotated = prefix + right + left
            if rotated < self.current:
                self.incorporate(rotated)

    def shrink_indices(self):
        # We take a bet that there is some monotonic lower bound such that
        # whenever current >= lower_bound the result works.
        for i in hrange(self.size):
            if self.current[i] == 0:
                continue

            if self.incorporate(
                self.current[:i] + hbytes([0]) + self.current[i + 1:]
            ):
                continue

            prefix = self.current[:i]
            original_suffix = self.current[i + 1:]

            for suffix in [
                original_suffix,
                hbytes([255]) * len(original_suffix),
            ]:
                minimize_byte(
                    self.current[i],
                    lambda c: self.current[i] == c or self.incorporate(
                        prefix + hbytes([c]) + suffix)
                )

    def run(self):
        if not any(self.current):
            return
        if len(self.current) == 1:
            minimize_byte(
                self.current[0],
                lambda c: c == self.current[0] or self.incorporate(hbytes([c]))
            )
            return

        # Initial checks as to whether the two smallest possible buffers of
        # this length can work. If so there's nothing to do here.
        if self.incorporate(hbytes(self.size)):
            return

        if self.incorporate(hbytes([0] * (self.size - 1) + [1])):
            return

        # Perform a binary search to try to replace a long initial segment with
        # zero bytes.
        # Note that because this property isn't monotonic this will not always
        # find the longest subsequence we can replace with zero, only some
        # subsequence.

        # Replacing the first nonzero bytes with zero does *not* work
        nonzero = len(self.current)

        # Replacing the first canzero bytes with zero *does* work.
        canzero = 0
        while self.current[canzero] == 0:
            canzero += 1

        base = self.current

        @binsearch(canzero, nonzero)
        def zero_prefix(mid):
            return self.incorporate(
                hbytes(mid) +
                base[mid:]
            )

        base = self.current

        @binsearch(0, self.size)
        def shift_right(mid):
            if mid == 0:
                return True
            if mid == self.size:
                return False
            return self.incorporate(hbytes(mid) + base[:-mid])

        change_counter = -1
        first = True
        while (
            (first or self.full) and
            change_counter < self.changes
        ):
            first = False
            change_counter = self.changes

            self.shift()
            self.shrink_indices()
            self.rotate_suffixes()


def minimize(initial, condition, random, full=True):
    """Perform a lexicographical minimization of the byte string 'initial' such
    that the predicate 'condition' returns True, and return the minimized
    string."""
    m = Minimizer(initial, condition, random, full)
    m.run()
    return m.current


def binsearch(_lo, _hi):
    """Run a binary search to find the point at which a function changes value
    between two bounds.

    This function is used purely for its side effects and returns
    nothing.

    """
    def accept(f):
        lo = _lo
        hi = _hi

        loval = f(lo)
        hival = f(hi)

        if loval == hival:
            return

        while lo + 1 < hi:
            mid = (lo + hi) // 2
            midval = f(mid)
            if midval == loval:
                lo = mid
            else:
                assert hival == midval
                hi = mid
    return accept


def minimize_byte(c, f):
    if f(0):
        return 0
    if c == 1 or f(1):
        return 1
    elif c == 2:
        return 2
    if f(c - 1):
        lo = 1
        hi = c - 1
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if f(mid):
                hi = mid
            else:
                lo = mid
        return hi
    else:
        return c
