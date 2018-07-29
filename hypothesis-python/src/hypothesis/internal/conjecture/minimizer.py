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

import sys
import math

from hypothesis.internal.compat import ceil, floor, hbytes, hrange, \
    int_to_bytes, int_from_bytes
from hypothesis.internal.conjecture.floats import is_simple, \
    float_to_lex, lex_to_float


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
            prefix = self.current[:i]
            suffix = self.current[i + 1:]

            minimize_int(
                self.current[i],
                lambda c: self.current[i] == c or self.incorporate(
                    prefix + hbytes([c]) + suffix)
            )

    def incorporate_int(self, i):
        return self.incorporate(int_to_bytes(i, self.size))

    def incorporate_float(self, f):
        assert self.size == 8
        return self.incorporate_int(float_to_lex(f))

    def float_hack(self):
        """Our encoding of floating point numbers does the right thing when you
        lexically shrink it, but there are some highly non-obvious lexical
        shrinks corresponding to natural floating point operations.

        We can't actually tell when the floating point encoding is being used
        (that would break the assumptions that Hypothesis doesn't inspect
        the generated values), but we can cheat: We just guess when it might be
        being used and perform shrinks that are valid regardless of our guess
        is correct.

        So that's what this method does. It's a cheat to give us good shrinking
        of floating at low cost in runtime and only moderate cost in elegance.
        """
        # If the block is of the wrong size then we're certainly not using the
        # float encoding.
        if self.size != 8:
            return

        # If the high bit is zero then we're in the integer representation of
        # floats so we don't need these hacks because it will shrink normally.
        if self.current[0] >> 7 == 0:
            return

        i = self.current_int
        f = lex_to_float(i)

        # This floating point number can be represented in our simple format.
        # So we try converting it to that (which will give the same float, but
        # a different encoding of it). If that doesn't work then the float
        # value of this doesn't unambiguously give the desired predicate, so
        # this approach isn't useful. If it *does* work, then we're now in a
        # situation where we don't need it, so either way we return here.
        if is_simple(f):
            self.incorporate_float(f)
            return

        # We check for a bunch of standard "large" floats. If we're currently
        # worse than them and the shrink downwards doesn't help, abort early
        # because there's not much useful we can do here.
        for g in [
            float('nan'), float('inf'), sys.float_info.max,
        ]:
            j = float_to_lex(g)
            if j < i:
                if self.incorporate_int(j):
                    f = g
                    i = j

        if math.isinf(f) or math.isnan(f):
            return

        # Finally we get to the important bit: Each of these is a small change
        # to the floating point number that corresponds to a large change in
        # the lexical representation. Trying these ensures that our floating
        # point shrink can always move past these obstacles. In particular it
        # ensures we can always move to integer boundaries and shrink past a
        # change that would require shifting the exponent while not changing
        # the float value much.
        for g in [floor(f), ceil(f)]:
            if self.incorporate_float(g):
                return

        if f > 2:
            self.incorporate_float(f - 1)

    @property
    def current_int(self):
        return int_from_bytes(self.current)

    def minimize_as_integer(self):
        minimize_int(
            self.current_int,
            lambda c: c == self.current_int or self.incorporate_int(c)
        )

    def sort(self):
        return self.incorporate(hbytes(sorted(self.current)))

    # Sometimes data can be sorted, except that some elements need to remain
    # in constant locations to preserve invariants that the minimizer can't be
    # aware of. Attempt to do as much sorting as possible.
    # This does not try to bring elements 'across' stationary elements.
    def partial_sort(self):
        any_sorting_done = False
        ps = list(self.current)
        for i in hrange(self.size - 1):
            j = i + 1
            while j > 0 and ps[j - 1] > ps[j]:
                prev_list = ps[:]
                ps[j], ps[j - 1] = ps[j - 1], ps[j]
                if self.incorporate(hbytes(ps)):
                    any_sorting_done = True
                else:  # Restore to the last usable found example
                    ps = prev_list
                j = j - 1
        return any_sorting_done

    def run(self):
        if not any(self.current):
            return
        if len(self.current) == 1:
            self.minimize_as_integer()
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

            self.sort()
            self.float_hack()
            self.shift()
            self.shrink_indices()
            self.rotate_suffixes()
            self.minimize_as_integer()
            self.partial_sort()


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


def minimize_int(c, f):
    """Return the smallest byte for which a function `f` returns True, starting
    with the byte `c` as an unsigned integer."""
    if c == 0:
        return 0
    if f(0):
        return 0
    if c == 1 or f(1):
        return 1
    elif c == 2:
        return 2
    if f(c - 1):
        hi = c - 1
    elif f(c - 2):
        hi = c - 2
    else:
        return c
    lo = 1
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if f(mid):
            hi = mid
        else:
            lo = mid
    return hi
