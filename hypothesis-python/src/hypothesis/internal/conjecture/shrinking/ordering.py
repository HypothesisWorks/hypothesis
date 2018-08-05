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

from hypothesis.internal.conjecture.shrinking.common import Shrinker, \
    find_integer


def identity(v):
    return v


class Ordering(Shrinker):
    def __init__(self, initial, predicate, random, full, key=identity):
        super(Ordering, self).__init__(initial, predicate, random, full)
        self.key = key

    def make_immutable(self, value):
        return tuple(value)

    def short_circuit(self):
        return len(self.current) <= 1 or self.consider(
            sorted(self.current, key=self.key))

    def left_is_better(self, left, right):
        return tuple(map(self.key, left)) < tuple(map(self.key, right))

    def invariant(self, value):
        assert len(value) == len(self.current)
        assert sorted(value) == sorted(self.current)

    def run_step(self):
        for i in range(len(self.current)):
            original = self.current

            def push_back(k):
                if k > i:
                    return False
                j = i - k
                if original[i] == original[j]:
                    return True
                if self.key(original[j]) < self.key(original[i]):
                    return False
                attempt = list(original)
                attempt[i], attempt[j] = attempt[j], attempt[i]
                return self.consider(attempt)

            find_integer(push_back)
