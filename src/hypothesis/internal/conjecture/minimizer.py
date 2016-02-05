# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

"""
This module implements a lexicographic minimizer for blocks of bytes.

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


from random import Random


class Minimizer(object):

    def __init__(self, initial, condition, random):
        self.current = initial
        self.size = len(self.current)
        self.condition = condition
        self.random = random or Random()
        self.changes = 0
        self.seen = set()
        self.considerations = 0
        self.duplicates = 0

    def incorporate(self, buffer):
        assert len(buffer) == self.size
        assert buffer <= self.current
        self.considerations += 1
        if buffer in self.seen:
            self.duplicates += 1
            return False
        self.seen.add(buffer)
        if self.condition(buffer):
            self.current = buffer
            self.changes += 1
            return True
        return False

    def run(self):
        if not any(self.current):
            return
        if self.incorporate(bytes(self.size)):
            return
        for c in range(max(self.current)):
            if self.incorporate(
                bytes(min(b, c) for b in self.current)
            ):
                break

        for i in range(self.size, 0, - 1):
            if self.incorporate(
                bytes(i) + self.current[i:]
            ):
                break

        change_counter = -1
        while self.current and change_counter < self.changes:
            change_counter = self.changes
            for _ in range(10):
                self.incorporate(
                    _draw_predecessor(self.random, self.current)
                )
            while True:
                i = int.from_bytes(self.current, 'big')
                i >>= 1
                if not self.incorporate(
                    i.to_bytes(self.size, 'big')
                ):
                    break
            for c in range(256):
                i = 0
                while i < self.size:
                    if self.current[i] > c:
                        if not self.incorporate(
                            self.current[:i] + bytes([c]) +
                            self.current[i + 1:]
                        ):
                            if (
                                i + 1 < self.size
                            ):
                                self.incorporate(
                                    self.current[:i] + bytes([c, 255]) +
                                    self.current[i + 2:]
                                ) or self.incorporate(
                                    self.current[:i] + bytes([c]) +
                                    bytes([255] * (self.size - i - 1))
                                )
                    i += 1


def minimize(initial, condition, random=None):
    m = Minimizer(initial, condition, random)
    m.run()
    return m.current


def _draw_predecessor(rnd, xs):
    r = bytearray()
    any_strict = False
    for x in xs:
        if not any_strict:
            c = rnd.randint(0, x)
            if c < x:
                any_strict = True
        else:
            c = rnd.randint(0, 255)
        r.append(c)
    return bytes(r)
