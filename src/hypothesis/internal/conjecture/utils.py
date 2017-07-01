# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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
from collections import Sequence, OrderedDict

from hypothesis._settings import note_deprecation
from hypothesis.internal.compat import floor, hbytes, bit_length, \
    int_from_bytes
from hypothesis.internal.floats import int_to_float


def n_byte_unsigned(data, n):
    return int_from_bytes(data.draw_bytes(n))


def saturate(n):
    bits = bit_length(n)
    k = 1
    while k < bits:
        n |= (n >> k)
        k *= 2
    return n


def integer_range(data, lower, upper, center=None):
    assert lower <= upper
    if lower == upper:
        return int(lower)

    if center is None:
        center = lower
    center = min(max(center, lower), upper)

    bits = bit_length(max(upper - center, center - lower))

    nbytes = bits // 8 + int(bits % 8 != 0)

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

    mask = saturate(gap)
    probe = gap + 1

    while probe > gap:
        probe = int_from_bytes(data.draw_bytes(nbytes)) & mask

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
    return bool(n_byte_unsigned(data, 1) & 1)


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

            i = data.draw_bytes(1)[0]

            # We always label the region that causes us to repeat the loop as
            # 255 so that shrinking this byte never causes us to need to draw
            # more data.
            if falsey + truthy < 256 and i == 255:
                p = remainder
                continue
            if falsey == 0:
                # Every other partition is truthy, so the result is true
                result = True
            elif truthy == 0:
                # Every other partition is falsey, so the result is true
                result = True
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


def write(data, string):
    data.write(string)


class Sampler(object):
    """Sampler based on "Succinct Sampling from Discrete Distributions" by
    Bringmann and Larsen. In general it has some advantages and disadvantages
    compared to the more normal alias method, but its big advantage for us is
    that it plays well with shrinking: The values are laid out in their natural
    order, so shrink in that order.

    Its big disadvantage is that for heavily biased distributions it can
    use a lot of memory. Solution is some mix of "don't do that then"
    and not worrying about it because Hypothesis is something of a
    memory hog anyway.

    """

    def __init__(self, weights):
        # We consider each weight expressed in terms of the average weight,
        # say t. We write the weight of i as nt + f, where n is an integer and
        # 0 <= f < 1. We then store n items for this weight which correspond
        # to drawing i unconditionally, and if f > 0 we store an additional
        # item that corresponds to drawing i with probability f. This ensures
        # that (under a uniform model) we draw i with probability proportionate
        # to its weight.

        # We then rearrange things to shrink better. The table with the whole
        # weights is kept in sorted order so that shrinking still corresponds
        # to shrinking leftwards. The fractional weights however are put in
        # a second table that is logically "to the right" of the whole weights
        # and are sorted in order of decreasing acceptance probaility. This
        # ensures that shrinking lexicographically always results in drawing
        # less data.
        self.table = []
        self.extras = []
        self.acceptance = []
        total = sum(weights)
        n = len(weights)
        for i, x in enumerate(weights):
            whole_occurrences = floor(x * n / total)
            acceptance = x - whole_occurrences
            self.acceptance.append(acceptance)
            for _ in range(whole_occurrences):
                self.table.append(i)
            if acceptance > 0:
                self.extras.append(i)
        self.extras.sort(key=self.acceptance.__getitem__, reverse=True)

    def sample(self, data):
        while True:
            data.start_example()
            # We always draw the acceptance data even if we don't need it,
            # because that way we keep the amount of data we use stable.
            i = integer_range(data, 0, len(self.table) + len(self.extras) - 1)
            if i < len(self.table):
                result = self.table[i]
                data.stop_example()
                return result
            else:
                result = self.extras[i - len(self.table)]
                accept = not biased_coin(data, 1 - self.acceptance[result])
                data.stop_example()
                if accept:
                    return result
