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

import math


def n_byte_unsigned(data, n):
    return int.from_bytes(data.draw_bytes(n), 'big')


def saturate(n):
    bits = n.bit_length()
    k = 1
    while k < bits:
        n |= (n >> k)
        k *= 2
    return n


def integer_range(data, lower, upper):
    assert lower <= upper
    if lower == upper:
        return lower
    gap = upper - lower
    bits = gap.bit_length()
    nbytes = bits // 8 + int(bits % 8 != 0)
    mask = saturate(gap)
    while True:
        probe = n_byte_unsigned(data, nbytes) & mask
        if probe <= gap:
            return lower + probe


def centered_integer_range(data, lower, upper, center):
    """Return an integer n such that lower <= n <= upper, but such that when
    shrinking it shrinks in the direction of center. It is not required that
    lower <= enter <= upper."""

    assert lower <= upper
    if lower == upper:
        return lower

    gap = upper - lower
    bits = gap.bit_length()
    nbytes = bits // 8 + int(bits % 8 != 0)
    mask = saturate(gap)

    while True:
        probe = n_byte_unsigned(data, nbytes) & mask
        if probe <= gap:
            if center >= upper:
                result = upper - probe
            elif center <= lower:
                result = lower + probe
            else:
                if center + probe <= upper:
                    result = center + probe
                else:
                    result = upper - probe
            assert lower <= result <= upper
            return result


def choice(data, values):
    return values[integer_range(data, 0, len(values) - 1)]


def geometric(data, p):
    denom = math.log1p(-p)
    n_bytes = 8

    def distribution(random, n):
        assert n == n_bytes
        for _ in range(100):
            try:
                return int(
                    math.log1p(-random.random()) / denom
                ).to_bytes(n_bytes, 'big')
            # This is basically impossible to hit but is required for
            # correctness
            except OverflowError:  # pragma: no cover
                pass
        # We got a one in a million chance 100 times in a row. Something is up.
        assert False  # pragma: no cover
    return int.from_bytes(data.draw_bytes(n_bytes, distribution), 'big')


def boolean(data):
    return bool(n_byte_unsigned(data, 1) & 1)


def biased_coin(data, p):
    def distribution(random, n):
        assert n == 1
        return bytes([int(random.random() <= p)])
    return bool(
        data.draw_bytes(1, distribution)[0] & 1
    )
