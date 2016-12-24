# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2016 David R. MacIver
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

import math

from hypothesis.internal.compat import bit_length


class VoseAliasSampler(object):
    """Samples integers from a weighted distribution using Vose's algorithm for
    the Alias Method.

    See http://www.keithschwarz.com/darts-dice-coins/ for details.

    """

    def __init__(self, weights):
        assert any(weights)

        n = len(weights)

        total = sum(weights)

        weights = tuple(float(w) / total for w in weights)

        self._alias = [None] * len(weights)
        self._probabilities = [None] * len(weights)

        self._size = total

        small = []
        large = []

        ps = [w * n for w in weights]

        for i, p in enumerate(ps):
            if p < 1:
                small.append(i)
            else:
                large.append(i)

        while small and large:
            l = small.pop()
            g = large.pop()
            assert ps[g] >= 1 >= ps[l]
            self._probabilities[l] = ps[l]
            self._alias[l] = g
            ps[g] = (ps[l] + ps[g]) - 1
            if ps[g] < 1:
                small.append(g)
            else:
                large.append(g)
        for q in [small, large]:
            while q:
                g = q.pop()
                self._probabilities[g] = 1.0
                self._alias[g] = g

        assert None not in self._alias
        assert None not in self._probabilities

    def sample(self, random):
        i = random.randint(0, len(self._probabilities) - 1)
        p = self._probabilities[i]

        if p >= 1:
            toss = True
        elif p <= 0:
            toss = False
        else:
            toss = random.random() <= p

        if toss:
            return i
        else:
            return self._alias[i]

    def __repr__(self):
        return 'Sampler(%r)' % (
            list(zip(
                range(len(self._probabilities)),
                self._probabilities, self._alias)),)


class UniformSampler(object):

    def __init__(self, values):
        self.values = tuple(values)
        assert len(self.values) > 1
        mask = len(self.values) - 1
        mask |= (mask >> 1)
        mask |= (mask >> 2)
        mask |= (mask >> 4)
        mask |= (mask >> 8)
        mask |= (mask >> 16)
        mask |= (mask >> 32)
        self.mask = mask
        self.nbits = bit_length(mask)
        self.n_draws = int(math.floor(32 / self.nbits))
        assert self.n_draws > 0
        self.queue = []

    def sample(self, random):
        while not self.queue:
            n = len(self.values)
            bits = random.getrandbits(32)
            for _ in range(self.n_draws):
                i = bits & self.mask
                if i < n:
                    self.queue.append(i)
                bits >>= self.nbits
        return self.values[self.queue.pop()]


class ConstantSampler(object):

    def __init__(self, value):
        self.value = value

    def sample(self, random):
        return self.value


cache = {}


def sampler(weights):
    weights = tuple(weights)
    try:
        return cache[weights]
    except KeyError:
        pass

    seen_weight = None
    has_only_one_weight = True
    for w in weights:
        if w:
            if seen_weight is None:
                seen_weight = w
            elif seen_weight != w:
                has_only_one_weight = False
                break
    if has_only_one_weight:
        values = tuple(i for i, w in enumerate(weights) if w)
        if len(values) > 1:
            result = UniformSampler(values)
        else:
            result = ConstantSampler(values[0])
    else:
        result = VoseAliasSampler(weights)
    cache[weights] = result
    return result
