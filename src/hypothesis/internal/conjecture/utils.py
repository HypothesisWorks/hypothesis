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

from array import array

from hypothesis.internal.compat import hbytes, bit_length, int_to_bytes, \
    int_from_bytes
from hypothesis.internal.conjecture.grammar import Literal, Interval, \
    Alternation


def n_byte_unsigned(data, n):
    return int_from_bytes(bytes(data.draw_byte() for _ in range(n)))


def saturate(n):
    bits = bit_length(n)
    k = 1
    while k < bits:
        n |= (n >> k)
        k *= 2
    return n


RANGE_CACHE = {}


def basic_integer_range(data, lower, upper):
    bits = max(bit_length(lower), bit_length(upper))
    nbytes = bits // 8 + int(bits % 8 != 0)
    key = (lower, upper)
    try:
        all_valid = RANGE_CACHE[key]
    except KeyError:
        all_valid = Interval(
            int_to_bytes(lower, nbytes),
            int_to_bytes(upper, nbytes))
        RANGE_CACHE[key] = all_valid
    return int_from_bytes(data.draw_from_grammar(all_valid))


def integer_range(data, lower, upper, center=None):
    assert lower <= upper
    if lower == upper:
        return int(lower)

    if center is None:
        return basic_integer_range(data, lower, upper)
    center = min(max(center, lower), upper)

    gap = upper - lower

    bits = bit_length(gap)
    nbytes = bits // 8 + int(bits % 8 != 0)

    max_string = int_to_bytes(gap, nbytes)
    all_valid = Interval(int_to_bytes(0, nbytes), max_string)

    special_integers = {0, 1, gap - 1, gap}
    if center > lower:
        special_integers.add(upper - center)

    special = Alternation(
        Literal(int_to_bytes(v, nbytes))
        for v in special_integers)

    if boolean(data):
        grammar = special
    else:
        grammar = all_valid

    i = int_from_bytes(data.draw_from_grammar(grammar))

    result = center + i
    if result > upper:
        result = center - (result - upper)
    assert lower <= result <= upper
    return result


def weighted_integer(data, weights):
    if len(weights) < 256:
        return data.draw_byte(weights)

    n = len(weights) >> 8
    assert n > 0
    bucket_weights = array('d', [0] * n)
    for i, c in enumerate(weights):
        bucket_weights[i >> 8] += c

    bucket = data.draw_byte(bucket_weights) << 8
    suffix_weights = array('d', [0] * 256)
    for i in range(256):
        if bucket + i >= len(weights):
            break
        suffix_weights[i] = weights[bucket + i]
    return bucket + data.draw_byte(suffix_weights)


def centered_integer_range(data, lower, upper, center):
    return integer_range(
        data, lower, upper, center=center
    )


def choice(data, values):
    return values[integer_range(data, 0, len(values) - 1)]


def geometric(data, p):
    weights = array('d', ((1 - p) ** i for i in range(256)))
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
    return bool(data.draw_byte(array('d', [1 - p, p])) & 1)


def write(data, string):
    weights = [0] * 256
    for c in hbytes(string):
        weights[c] = 1
        data.draw_byte(weights)
        weights[c] = 0
