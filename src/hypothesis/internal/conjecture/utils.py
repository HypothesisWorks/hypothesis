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

from hypothesis.internal.compat import bit_length, int_to_bytes, \
    int_from_bytes
from hypothesis.internal.conjecture.grammar import Interval


def n_byte_unsigned(data, n):
    return int_from_bytes(bytes(data.draw_byte() for _ in range(n)))


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
    if lower < center < upper:
        def distribution(random):
            if random.randint(0, 1):
                return random.randint(center, upper)
            else:
                return random.randint(lower, center)
    else:
        def distribution(random):
            return random.randint(lower, upper)

    gap = upper - lower

    bits = bit_length(gap)
    nbytes = bits // 8 + int(bits % 8 != 0)

    i = int_from_bytes(
        data.draw_from_grammar(
            Interval(b'\0' * nbytes, int_to_bytes(gap, nbytes)))
    )

    result = center + i
    if result > upper:
        result = center - (result - upper)
    assert lower <= result <= upper
    return result


def integer_range_with_distribution(data, lower, upper, distribution):
    assert lower <= upper
    if lower == upper:
        return int(lower)

    assert distribution is not None

    gap = upper - lower
    bits = bit_length(gap)
    nbytes = bits // 8 + int(bits % 8 != 0)
    mask = saturate(gap)

    def byte_distribution(random, n):
        assert n == nbytes
        return int_to_bytes(distribution(random), n)

    result = gap + 1

    while result > gap:
        result = int_from_bytes(
            data.draw_bytes(nbytes, byte_distribution)
        ) & mask

    assert lower <= result <= upper
    return int(result)


def centered_integer_range(data, lower, upper, center):
    return integer_range(
        data, lower, upper, center=center
    )


def choice(data, values):
    return values[integer_range(data, 0, len(values) - 1)]


def geometric(data, p):
    weights = tuple((1 - p) ** i for i in range(256))
    result = 0
    while True:
        i = data.draw_byte(weights)
        if i < 255:
            return result + i
        else:
            result += 255


def boolean(data):
    return biased_coin(data, 0.5)


def biased_coin(data, p):
    return bool(data.draw_byte([1 - p, p]) & 1)


def write(data, string):
    weights = [0] * 256
    for c in string:
        weights[c] = 1
        data.draw_byte(weights)
        weights[c] = 0
