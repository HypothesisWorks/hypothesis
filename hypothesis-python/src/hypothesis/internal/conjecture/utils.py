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
import hashlib
from fractions import Fraction
from collections import Sequence, OrderedDict

from hypothesis._settings import note_deprecation
from hypothesis.internal.compat import ceil, floor, hbytes, hrange, \
    qualname, bit_length, str_to_bytes, int_from_bytes
from hypothesis.internal.floats import int_to_float

LABEL_MASK = 2 ** 64 - 1


def calc_label_from_name(name):
    hashed = hashlib.md5(str_to_bytes(name)).digest()
    return int_from_bytes(hashed[:8])


def calc_label_from_cls(cls):
    return calc_label_from_name(qualname(cls))


def combine_labels(*labels):
    label = 0
    for l in labels:
        label = (label << 1) & LABEL_MASK
        label ^= l
    return label


INTEGER_RANGE_DRAW_LABEL = calc_label_from_name(
    'another draw in integer_range()')
GEOMETRIC_LABEL = calc_label_from_name('geometric()')
BIASED_COIN_LABEL = calc_label_from_name('biased_coin()')
SAMPLE_IN_SAMPLER_LABLE = calc_label_from_name('a sample() in Sampler')
ONE_FROM_MANY_LABEL = calc_label_from_name('one more from many()')


def integer_range(data, lower, upper, center=None):
    assert lower <= upper
    if lower == upper:
        # Write a value even when this is trival so that when a bound depends
        # on other values we don't suddenly disappear when the gap shrinks to
        # zero - if that happens then often the data stream becomes misaligned
        # and we fail to shrink in cases where we really should be able to.
        data.write(hbytes([0]))
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
        data.start_example(INTEGER_RANGE_DRAW_LABEL)
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


try:
    from numpy import ndarray
except ImportError:  # pragma: no cover
    ndarray = ()


def check_sample(values, strategy_name):
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
    elif not isinstance(values, (OrderedDict, Sequence, enum.EnumMeta)):
        note_deprecation(
            'Cannot sample from {values}, not an ordered collection. '
            'Hypothesis goes to some length to ensure that the {strategy} '
            'strategy has stable results between runs. To replay a saved '
            'example, the sampled values must have the same iteration order '
            'on every run - ruling out sets, dicts, etc due to hash '
            'randomisation. Most cases can simply use `sorted(values)`, but '
            'mixed types or special values such as math.nan require careful '
            'handling - and note that when simplifying an example, '
            'Hypothesis treats earlier values as simpler.'.format(
                values=repr(values), strategy=strategy_name))
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
    data.start_example(GEOMETRIC_LABEL)
    while True:
        probe = fractional_float(data)
        if probe < 1.0:
            result = int(math.log1p(-probe) / denom)
            assert result >= 0, (probe, p, result)
            data.stop_example()
            return result


def boolean(data):
    return bool(data.draw_bits(1))


class Coin(object):
    def __init__(self, p):
        self.probability = p
        assert 0 < p < 1

        n_bits = 1
        while True:
            opts = 2 ** n_bits
            falsey = floor(opts * (1 - p))
            truthy = floor(opts * p)
            if min(falsey, truthy) == 0:
                n_bits *= 2
            else:
                break
        self.n_bits = n_bits
        self.n_bytes = ceil(n_bits / 8)
        self.true = hbytes(self.n_bytes - 1) + hbytes([1])
        self.false = hbytes(self.n_bytes)

    def rig(self, data, result):
        if result:
            data.write(self.true)
        else:
            data.write(self.false)

    def flip(self, data):
        data.start_example(BIASED_COIN_LABEL)
        while True:
            # The logic here is a bit complicated and special cased to make it
            # play better with the shrinker.

            # We imagine partitioning the real interval [0, 1] into 2**n equal
            # parts and looking at each part and whether its interior is wholly
            # <= p or wholly >= p. At most one part can be neither.

            # We then pick a random part. If it's wholly on one side or the
            # other of p then we use that as the answer. If p is contained in
            # the interval then we start again with a new probability that is
            # given by the fraction of that interval that was <= our previous
            # p.

            # We then take advantage of the fact that we have control of the
            # labelling to make this shrink better, using the following tricks:

            # If p is <= 0 or >= 1 the result of this coin is certain. We make
            # sure to write to the data stream anyway so that these don't cause
            # difficulties when shrinking. Note that we ensured that this can't
            # happen on the first iteration of the loop, but there's nothing to
            # stop it happening on a later one.
            p = self.probability
            opts = 2 ** self.n_bits
            falsey = floor(opts * (1 - p))
            truthy = floor(opts * p)
            if p <= 0:
                self.rig(data, False)
                result = False
            elif p >= 1:
                self.rig(data, True)
                result = True
            else:
                remainder = opts * p - truthy

                if falsey + truthy == opts:
                    if isinstance(p, Fraction):
                        m = p.numerator
                        n = p.denominator
                    else:
                        m, n = p.as_integer_ratio()
                    assert n & (n - 1) == 0, n  # n is a power of 2
                    assert n > m > 0
                    truthy = m
                    falsey = n - m
                    partial = False
                else:
                    partial = True

                i = data.draw_bits(self.n_bits)

                # We always label the region that causes us to repeat the loop
                # is opts - 1 so that shrinking this byte never causes us to
                # need to draw more data.
                if partial and i + 1 == opts:
                    p = remainder
                    continue
                if i <= 1:
                    # We arrange it so that zero is always false and 1 is
                    # always true which makes shrinking easier because we can
                    # always replace a truthy block with 1. This has the
                    # slightly weird property that shrinking from 2 to 1 can
                    # cause the result to grow, but the shrinker always tries 0
                    # and 1 first anyway, so this will usually be fine.
                    result = bool(i)
                else:
                    # Originally everything in the region 0 <= i < falsey was
                    # false and everything above was true. We swapped one
                    # truthy element into this region, so the region becomes
                    # 0 <= i <= falsey except for i = 1. We know i > 1 here, so
                    # the test for truth becomes i > falsey.
                    result = i > falsey
            break
        data.stop_example()
        return result


def biased_coin(data, p):
    """Return False with probability p (assuming a uniform generator),
    shrinking towards False.

    If force is set to True or False then this will return that value
    but set the byte stream up as if it have flipped the coin.
    """
    return Coin(p).flip(data)


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
        data.start_example(SAMPLE_IN_SAMPLER_LABLE)
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
        assert 0 <= min_size <= average_size <= max_size
        self.min_size = min_size
        self.max_size = max_size
        self.data = data
        self.coin = Coin(1 - 1.0 / (1 + average_size))
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
            self.coin.rig(self.data, False)
            should_continue = False
        else:
            if self.count < self.min_size:
                self.coin.rig(self.data, True)
                should_continue = True
            elif self.count >= self.max_size:
                self.coin.rig(self.data, False)
                should_continue = True
            else:
                should_continue = self.coin.flip(self.data)

        if should_continue:
            self.data.start_example(ONE_FROM_MANY_LABEL)
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
