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
        self.considerations += 1
        if buffer in self.seen:
            self.duplicates += 1
            return False
        self.seen.add(buffer)
        assert len(buffer) < len(self.current) or \
            (len(buffer) == len(self.current) and buffer < self.current)
        if self.condition(buffer):
            self.current = buffer
            self.changes += 1
            return True
        return False

    def run(self):
        n = len(self.current)
        for i in range(n, 0, -1):
            if self.incorporate(self.current[i:]):
                break
        change_counter = -1
        while self.current and change_counter < self.changes:
            change_counter = self.changes
            i = 0
            while i < len(self.current):
                if not self.incorporate(
                    self.current[:i] + self.current[i + 1:]
                ):
                    i += 1
            if change_counter < self.changes:
                continue
            if not any(self.current):
                break
            for c in range(256):
                b = bytes([c])
                i = 0
                while i < len(self.current):
                    if self.current[i] > c:
                        self.incorporate(
                            self.current[:i] + b + self.current[i + 1:]
                        )
                    i += 1
            for c in range(256):
                if self.current.count(c) > 1:
                    for d in range(c):
                        if self.incorporate(bytes(
                            d if t == c else t for t in self.current
                        )):
                            break
            i = 1
            while i < len(self.current):
                if self.current[i] == 0 and self.current[i - 1] > 0:
                    self.incorporate(
                        self.current[:i - 1] + bytes([
                            self.current[i - 1] - 1, 255
                        ]) + self.current[i + 1:]
                    )
                i += 1
            if change_counter < self.changes:
                continue
            i = 0
            while i < len(self.current):
                j = i + 1
                counter = 0
                while j < len(self.current) and counter < 32:
                    if self.current[i] == self.current[j]:
                        counter += 1
                        for c in range(self.current[i]):
                            b = bytes([c])
                            r = self.current[:i] + b + self.current[i + 1:j] +\
                                b + self.current[j + 1:]
                            assert len(r) == len(self.current)
                            assert r < self.current
                            if self.incorporate(r):
                                break
                            if (
                                i + 1 < j and j + 1 < len(self.current) and (
                                    self.current[i + 1] < 255 or
                                    self.current[j + 1] < 255)
                            ):
                                replace = self.current[:i] + \
                                    bytes([self.current[i] - 1, 255]) + \
                                    self.current[i + 2:j] + \
                                    bytes([self.current[j] - 1, 255]) + \
                                    self.current[j + 2:]
                                assert len(replace) == len(self.current)
                                assert replace < self.current
                                if self.incorporate(replace):
                                    break
                    j += 1
                i += 1


def minimize(initial, condition, random=None):
    m = Minimizer(initial, condition, random)
    m.run()
    return m.current
