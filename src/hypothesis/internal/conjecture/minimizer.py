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

    def __init__(self, initial, condition, random, cautious):
        self.current = hbytes(initial)
        self.size = len(self.current)
        self.condition = condition
        self.random = random
        self.cautious = cautious
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
        if self.cautious:
            for c, b in zip(buffer, self.current):
                assert c <= b, (buffer, self.current)
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

    def shrink_indices(self, timid):
        assert timid or not self.cautious

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

            suffixes = [original_suffix]

            if not timid:
                suffixes.append(hbytes([255] * (self.size - i - 1)))

            for suffix in suffixes:

                def suitable(c):
                    """Does the lexicographically largest value starting with
                    our prefix and having c at i satisfy the condition?"""

                    return self.incorporate(prefix + hbytes([c]) + suffix)

                c = self.current[i]

                if (
                    # We first see if replacing the byte with zero and the rest
                    # is enough to trigger the condition. If this succeeds
                    # we've successfully zeroed the byte here and the rest of
                    # this search isn't useful. Note that we've already checked
                    # this for the existing suffix, but the caching makes that
                    # harmlesss.
                    not suitable(0) and

                    # We now check if the lexicographic predecessor (where this
                    # element is reduced by 1 and all subsequent elements are
                    # raised to 255) is valid here. If it's not then there's
                    # no point in trying the search and we can break out early.
                    suitable(c - 1)
                ):
                    # We now do a binary search to find a small value
                    # where the large suffix works. Again, the property is not
                    # necessarily monotonic, so this doesn't actually guarantee
                    # the smallest value.
                    @binsearch(0, self.current[i])
                    def _(m):
                        # We have to manually check the end point because we
                        # already incorporated this.
                        if m == self.current[i]:
                            return True
                        return suitable(m)

    def run(self):
        if not any(self.current):
            return
        if len(self.current) == 1:
            for c in hrange(self.current[0]):
                if self.incorporate(hbytes([c])):
                    break
            return

        # Initial checks as to whether the two smallest possible buffers of
        # this length can work. If so there's nothing to do here.
        if self.incorporate(hbytes(self.size)):
            return

        if not self.cautious or self.current[-1] > 0:
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

        if not self.cautious:
            @binsearch(0, self.size)
            def shift_right(mid):
                if mid == 0:
                    return True
                if mid == self.size:
                    return False
                return self.incorporate(hbytes(mid) + base[:-mid])

        change_counter = -1
        while self.current and change_counter < self.changes:
            change_counter = self.changes

            self.shift()
            self.shrink_indices(timid=True)

            if not self.cautious:
                self.shrink_indices(timid=False)
                self.rotate_suffixes()


def minimize(initial, condition, random, cautious=False):
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
