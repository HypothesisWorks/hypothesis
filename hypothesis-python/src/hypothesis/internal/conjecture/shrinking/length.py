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

from hypothesis.internal.conjecture.shrinking.common import find_integer


"""
This module implements a length minimizer for sequences.

That is, given some sequence of elements satisfying some predicate, it tries to
find a strictly shorter one satisfying the same predicate.

Doing so perfectly is provably exponential. This only implements a linear time
worst case algorithm which guarantees certain minimality properties of the
fixed point.
"""


class LengthShrinker(object):
    def __init__(self, initial, predicate):
        self.current = tuple(initial)
        self.__predicate = predicate
        self.__change_count = 0
        self.__seen = set()

    def incorporate(self, value):
        assert len(value) <= len(self.current)
        key = tuple(value)
        if key in self.__seen:
            return False
        self.__seen.add(key)
        if self.__predicate(value):
            self.__change_count += 1
            self.current = key
            return True
        return False

    def consider(self, value):
        return value == self.current or self.incorporate(value)

    def run(self):
        j = 0
        while j < len(self.current):
            i = len(self.current) - 1 - j
            start = self.current
            find_integer(
                lambda k: k <= i and self.consider(
                    start[:i + 1 - k] + start[i + 1:]
                )
            )
            j += 1
        if self.__change_count == 0:
            i = 0
            while i + 1 < len(self.current):
                self.incorporate(self.current[:i] + self.current[i + 2:])
                i += 1


def shrink_length(ls, f):
    """Attempt to find a smaller sequence satisfying f. Will only perform
    linearly many evaluations, and does not loop to a fixed point.

    Guarantees made at a fixed point:

        1. No individual element may be deleted.
        2. No *adjacent* pair of elements may be deleted.
    """
    empty = ls[:0]
    if f(empty):
        return empty
    if len(ls) <= 1:
        return ls
    s = LengthShrinker(ls, f)
    s.run()
    return s.current
