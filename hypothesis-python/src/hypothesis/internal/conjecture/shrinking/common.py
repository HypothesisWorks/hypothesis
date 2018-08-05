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


"""This module implements various useful common functions for shrinking tasks.
"""


def find_integer(f):
    """Finds a (hopefully large) integer such that f(n) is True and f(n + 1) is
    False.

    f(0) is assumed to be True and will not be checked.
    """
    # We first do a linear scan over the small numbers and only start to do
    # anything intelligent if f(4) is true. This is because it's very hard to
    # win big when the result is small. If the result is 0 and we try 2 first
    # then we've done twice as much work as we needed to!
    for i in range(1, 5):
        if not f(i):
            return i - 1

    # We now know that f(4) is true. We want to find some number for which
    # f(n) is *not* true.
    # lo is the largest number for which we know that f(lo) is true.
    lo = 4

    # Exponential probe upwards until we find some value hi such that f(hi)
    # is not true. Subsequently we maintain the invariant that hi is the
    # smallest number for which we know that f(hi) is not true.
    hi = 5
    while f(hi):
        lo = hi
        hi *= 2

    # Now binary search until lo + 1 = hi. At that point we have f(lo) and not
    # f(lo + 1), as desired..
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if f(mid):
            lo = mid
        else:
            hi = mid
    return lo


class Shrinker(object):
    """A Shrinker object manages a single value and a predicate it should
    satisfy, and attempts to improve it in some direction, making it smaller
    and simpler."""

    def __init__(self, initial, predicate, random, full):
        self.current = self.make_immutable(initial)
        self.random = random
        self.full = full
        self.changes = 0

        self.__predicate = predicate
        self.__seen = set()

    @classmethod
    def shrink(cls, initial, predicate, random, full=False, **kwargs):
        """Shrink the value ``initial`` subject to the constraint that it
        satisfies ``predicate``.

        Returns the shrunk value.
        """
        shrinker = cls(initial, predicate, random, full, **kwargs)
        shrinker.run()
        return shrinker.current

    def run(self):
        """Run for an appropriate number of steps to improve the current value.

        If self.full is True, will run until no further improvements can
        be found.
        """
        if self.short_circuit():
            return
        if self.full:
            prev = -1
            while self.changes != prev:
                prev = self.changes
                self.run_step()
        else:
            self.run_step()

    def incorporate(self, value):
        """Try using ``value`` as a possible candidate improvement.

        Return True if it works.
        """
        value = self.make_immutable(value)
        self.check_invariants(value)
        if not self.left_is_better(value, self.current):
            return False
        if value in self.__seen:
            return False
        self.__seen.add(value)
        if self.__predicate(value):
            self.changes += 1
            self.current = value
            return True
        return False

    def consider(self, value):
        """Returns True if make_immutable(value) == self.current after calling
        self.incorporate(value)."""
        value = self.make_immutable(value)
        if value == self.current:
            return True
        return self.incorporate(value)

    def make_immutable(self, value):
        """Convert value into an immutable (and hashable) representation of
        itself.

        It is these immutable versions that the shrinker will work on.

        Defaults to just returning the value.
        """
        return value

    def check_invariants(self, value):
        """Make appropriate assertions about the value to ensure that it is
        valid for this shrinker.

        Does nothing by default.
        """
        pass

    def short_circuit(self):
        """Possibly attempt to do some shrinking.

        If this returns True, the ``run`` method will terminate early
        without doing any more work.
        """
        raise NotImplementedError()

    def left_is_better(self, left, right):
        """Returns True if the left is strictly simpler than the right
        according to the standards of this shrinker."""
        raise NotImplementedError()

    def run_step(self):
        """Run a single step of the main shrink loop, attempting to improve the
        current value."""
        raise NotImplementedError()
