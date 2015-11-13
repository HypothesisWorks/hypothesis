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


def n_bit_unsigned(data, n):
    bn = int(math.ceil(n / 8))
    return n_byte_unsigned(data, bn) & ((1 << n) - 1)


def byte(data):
    return n_byte_unsigned(data, 1)


def n_byte_signed(data, n):
    if n == 0:
        return 0
    result = int.from_bytes(data.draw_bytes(n), 'big')
    mask = 1 << (n * 8 - 1)
    if result & mask:
        result = -(result ^ mask)
    return result


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


def choice(data, values):
    return values[integer_range(data, 0, len(values) - 1)]


def fractional_float(data):
    i = n_byte_unsigned(data, 4)
    x = i / (2 ** 32 - 1)
    if 0 < x < 1:
        return x
    data.mark_invalid()


def geometric(data, p):
    probe = 1.0 - fractional_float(data)
    if p >= 1.0:
        return 0
    denom = math.log1p(-p)
    return int(math.log(probe) / denom)


def boolean(data):
    return bool(n_byte_unsigned(data, 1) & 1)
