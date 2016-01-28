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

from random import Random

MASKS = [
    1 << i for i in range(8)
]


class Minimizer(object):

    def __init__(self, initial, condition, random):
        self.current = initial
        self.condition = condition
        self.random = random or Random()
        self.changes = 0
        self.seen = set()
        self.considerations = 0
        self.duplicates = 0

    def incorporate(self, buffer):
        assert len(buffer) == len(self.current)
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
        if self.incorporate(bytes(len(self.current))):
            return
        for c in range(max(self.current)):
            if self.incorporate(
                bytes(min(b, c) for b in self.current)
            ):
                break

        change_counter = -1
        while self.current and change_counter < self.changes:
            change_counter = self.changes
            for c in range(256):
                i = 0
                while i < len(self.current):
                    if self.current[i] > c:
                        if not self.incorporate(
                            self.current[:i] + bytes([c]) +
                            self.current[i + 1:]
                        ):
                            if (
                                i + 1 < len(self.current) and
                                self.current[i + 1] == 0
                            ):
                                self.incorporate(
                                    self.current[:i] + bytes([c, 255]) +
                                    self.current[i + 2:]
                                )
                    i += 1


def minimize(initial, condition, random=None):
    m = Minimizer(initial, condition, random)
    m.run()
    return m.current
