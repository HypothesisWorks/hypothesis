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

import enum
import math
import heapq
from fractions import Fraction
from collections import Sequence, OrderedDict

from hypothesis._settings import note_deprecation
from hypothesis.internal.compat import floor, hbytes, hrange, bit_length, \
    int_from_bytes
from hypothesis.internal.floats import int_to_float


def integer_range(data, lower, upper, center=None):
    assert lower <= upper
    if lower == upper:
        return int(lower)

    if center is None:
        center = lower
    center = min(max(center, lower), upper)

    if center == upper:
        above = False
    elif center == lower:
        above = True
    else:
        above = boolean(data)

    if above:
        gap = upper - center
    else:
        gap = center - lower

    assert gap > 0

    bits = bit_length(gap)
    probe = gap + 1

    while probe > gap:
        data.start_example()
        probe = data.draw_bits(bits)
        data.stop_example(discard=probe > gap)

    if above:
        result = center + probe
    else:
        result = center - probe

    assert lower <= result <= upper
    return int(result)


def centered_integer_range(data, lower, upper, center):
    return integer_range(
        data, lower, upper, center=center
    )


def check_sample(values):
    try:
        from numpy import ndarray
        if isinstance(values, ndarray):
            if values.ndim != 1:
                note_deprecation((
                    'Only one-dimensional arrays are supported for sampling, '
                    'and the given value has {ndim} dimensions (shape '
                    '{shape}).  This array would give samples of array slices '
                    'instead of elements!  Use np.ravel(values) to convert '
                    'to a one-dimensional array, or tuple(values) if you '
                    'want to sample slices.  Sampling a multi-dimensional '
                    'array will be an error in a future version of Hypothesis.'
                ).format(ndim=values.ndim, shape=values.shape))
            return tuple(values)
    except ImportError:  # pragma: no cover
        pass

    if not isinstance(values, (OrderedDict, Sequence, enum.EnumMeta)):
        note_deprecation(
            ('Cannot sample from %r, not a sequence.  ' % (values,)) +
            'Hypothesis goes to some length to ensure that sampling an '
            'element from a collection (with `sampled_from` or `choices`) is '
            'replayable and can be minimised.  To replay a saved example, '
            'the sampled values must have the same iteration order on every '
            'run - ruling out sets, dicts, etc due to hash randomisation.  '
            'Most cases can simply use `sorted(values)`, but mixed types or '
            'special values such as math.nan require careful handling - and '
            'note that when simplifying an example, Hypothesis treats '
            'earlier values as simpler.')
    return tuple(values)


def choice(data, values):
    return values[integer_range(data, 0, len(values) - 1)]


def getrandbits(data, n):
    n_bytes = n // 8
    if n % 8 != 0:
        n_bytes += 1
    return int_from_bytes(data.draw_bytes(n_bytes)) & ((1 << n) - 1)


FLOAT_PREFIX = 0b1111111111 << 52
FULL_FLOAT = int_to_float(FLOAT_PREFIX | ((2 << 53) - 1)) - 1


def fractional_float(data):
    return (
        int_to_float(FLOAT_PREFIX | getrandbits(data, 52)) - 1
    ) / FULL_FLOAT


def geometric(data, p):
    denom = math.log1p(-p)

    data.start_example()
    while True:
        probe = fractional_float(data)
        if probe < 1.0:
            result = int(math.log1p(-probe) / denom)
            assert result >= 0, (probe, p, result)
            data.stop_example()
            return result


def boolean(data):
    return bool(data.draw_bits(1))


def biased_coin(data, p):
    """Return False with probability p (assuming a uniform generator),
    shrinking towards False."""
    data.start_example()
    while True:
        # The logic here is a bit complicated and special cased to make it
        # play better with the shrinker.

        # We imagine partitioning the real interval [0, 1] into 256 equal parts
        # and looking at each part and whether its interior is wholly <= p
        # or wholly >= p. At most one part can be neither.

        # We then pick a random part. If it's wholly on one side or the other
        # of p then we use that as the answer. If p is contained in the
        # interval then we start again with a new probability that is given
        # by the fraction of that interval that was <= our previous p.

        # We then take advantage of the fact that we have control of the
        # labelling to make this shrink better, using the following tricks:

        # If p is <= 0 or >= 1 the result of this coin is certain. We make sure
        # to write a byte to the data stream anyway so that these don't cause
        # difficulties when shrinking.
        if p <= 0:
            data.write(hbytes([0]))
            result = False
        elif p >= 1:
            data.write(hbytes([1]))
            result = True
        else:
            falsey = floor(256 * (1 - p))
            truthy = floor(256 * p)
            remainder = 256 * p - truthy

            if falsey + truthy == 256:
                if isinstance(p, Fraction):
                    m = p.numerator
                    n = p.denominator
                else:
                    m, n = p.as_integer_ratio()
                assert n & (n - 1) == 0, n  # n is a power of 2
                assert n > m > 0
                truthy = m
                falsey = n - m
                bits = bit_length(n) - 1
                partial = False
            else:
                bits = 8
                partial = True

            i = data.draw_bits(bits)

            # We always label the region that causes us to repeat the loop as
            # 255 so that shrinking this byte never causes us to need to draw
            # more data.
            if partial and i == 255:
                p = remainder
                continue
            if falsey == 0:
                # Every other partition is truthy, so the result is true
                result = True
            elif truthy == 0:
                # Every other partition is falsey, so the result is false
                result = False
            elif i <= 1:
                # We special case so that zero is always false and 1 is always
                # true which makes shrinking easier because we can always
                # replace a truthy block with 1. This has the slightly weird
                # property that shrinking from 2 to 1 can cause the result to
                # grow, but the shrinker always tries 0 and 1 first anyway, so
                # this will usually be fine.
                result = bool(i)
            else:
                # Originally everything in the region 0 <= i < falsey was false
                # and everything above was true. We swapped one truthy element
                # into this region, so the region becomes 0 <= i <= falsey
                # except for i = 1. We know i > 1 here, so the test for truth
                # becomes i > falsey.
                result = i > falsey
        break
    data.stop_example()
    return result


class Sampler(object):
    """Sampler based on Vose's algorithm for the alias method. See
    http://www.keithschwarz.com/darts-dice-coins/ for a good explanation.

    The general idea is that we store a table of triples (base, alternate, p).
    base. We then pick a triple uniformly at random, and choose its alternate
    value with probability p and else choose its base value. The triples are
    chosen so that the resulting mixture has the right distribution.

    We maintain the following invariants to try to produce good shrinks:

    1. The table is in lexicographic (base, alternate) order, so that choosing
       an earlier value in the list always lowers (or at least leaves
       unchanged) the value.
    2. base[i] < alternate[i], so that shrinking the draw always results in
       shrinking the chosen element.

    """

    def __init__(self, weights):

        n = len(weights)

        self.table = [[i, None, None] for i in hrange(n)]

        total = sum(weights)

        num_type = type(total)

        zero = num_type(0)
        one = num_type(1)

        small = []
        large = []

        probabilities = [w / total for w in weights]
        scaled_probabilities = []

        for i, p in enumerate(probabilities):
            scaled = p * n
            scaled_probabilities.append(scaled)
            if scaled == 1:
                self.table[i][2] = zero
            elif scaled < 1:
                small.append(i)
            else:
                large.append(i)
        heapq.heapify(small)
        heapq.heapify(large)

        while small and large:
            lo = heapq.heappop(small)
            hi = heapq.heappop(large)

            assert lo != hi
            assert scaled_probabilities[hi] > one
            assert self.table[lo][1] is None
            self.table[lo][1] = hi
            self.table[lo][2] = one - scaled_probabilities[lo]
            scaled_probabilities[hi] = (
                scaled_probabilities[hi] + scaled_probabilities[lo]) - one

            if scaled_probabilities[hi] < 1:
                heapq.heappush(small, hi)
            elif scaled_probabilities[hi] == 1:
                self.table[hi][2] = zero
            else:
                heapq.heappush(large, hi)
        while large:
            self.table[large.pop()][2] = zero
        while small:
            self.table[small.pop()][2] = zero

        for entry in self.table:
            assert entry[2] is not None
            if entry[1] is None:
                entry[1] = entry[0]
            elif entry[1] < entry[0]:
                entry[0], entry[1] = entry[1], entry[0]
                entry[2] = one - entry[2]
        self.table.sort()

    def sample(self, data):
        data.start_example()
        i = integer_range(data, 0, len(self.table) - 1)
        base, alternate, alternate_chance = self.table[i]
        use_alternate = biased_coin(data, alternate_chance)
        data.stop_example()
        if use_alternate:
            return alternate
        else:
            return base


class many(object):
    """Utility class for collections. Bundles up the logic we use for "should I
    keep drawing more values?" and handles starting and stopping examples in
    the right place.

    Intended usage is something like:

    elements = many(data, ...)
    while elements.more():
        add_stuff_to_result()

    """

    def __init__(self, data, min_size, max_size, average_size):
        self.min_size = min_size
        self.max_size = max_size
        self.data = data
        self.stopping_value = 1 - 1.0 / (1 + average_size)
        self.count = 0
        self.rejections = 0
        self.drawn = False
        self.force_stop = False
        self.rejected = False

    def more(self):
        """Should I draw another element to add to the collection?"""
        if self.drawn:
            self.data.stop_example(discard=self.rejected)

        self.drawn = True
        self.rejected = False

        if self.min_size == self.max_size:
            should_continue = self.count < self.min_size
        elif self.force_stop:
            should_continue = False
        else:
            if self.count < self.min_size:
                p_continue = 1.0
            elif self.count >= self.max_size:
                p_continue = 0.0
            else:
                p_continue = self.stopping_value
            should_continue = biased_coin(self.data, p_continue)

        if should_continue:
            self.data.start_example()
            self.count += 1
            return True
        else:
            return False

    def reject(self):
        """Reject the last example (i.e. don't count it towards our budget of
        elements because it's not going to go in the final collection)."""
        assert self.count > 0
        self.count -= 1
        self.rejections += 1
        self.rejected = True
        if self.rejections > 2 * self.count:
            if self.count < self.min_size:
                self.data.mark_invalid()
            else:
                self.force_stop = True
