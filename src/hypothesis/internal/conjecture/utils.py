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
from hypothesis.internal.compat import hbytes, bit_length, int_to_bytes, \
    int_from_bytes


def n_byte_unsigned(data, n):
    return int_from_bytes(data.draw_bytes(n))


def saturate(n):
    bits = bit_length(n)
    k = 1
    while k < bits:
        n |= (n >> k)
        k *= 2
    return n


def integer_range(data, lower, upper, center=None, distribution=None):
    assert lower <= upper
    if lower == upper:
        return int(lower)

    if center is None:
        center = lower
    center = min(max(center, lower), upper)
    if distribution is None:
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
    mask = saturate(gap)

    def byte_distribution(random, n):
        assert n == nbytes
        v = distribution(random)
        if v >= center:
            probe = v - center
        else:
            probe = upper - v
        return int_to_bytes(probe, n)

    probe = gap + 1

    while probe > gap:
        probe = int_from_bytes(
            data.draw_bytes(nbytes, byte_distribution)
        ) & mask

    if center == upper:
        result = upper - probe
    elif center == lower:
        result = lower + probe
    else:
        if center + probe <= upper:
            result = center + probe
        else:
            result = upper - probe
    assert lower <= result <= upper
    return int(result)


def integer_range_with_distribution(data, lower, upper, nums):
    return integer_range(
        data, lower, upper, distribution=nums
    )


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


def geometric(data, p):
    denom = math.log1p(-p)
    n_bytes = 8

    def distribution(random, n):
        assert n == n_bytes
        for _ in range(100):
            try:
                return int_to_bytes(int(
                    math.log1p(-random.random()) / denom), n)
            # This is basically impossible to hit but is required for
            # correctness
            except OverflowError:  # pragma: no cover
                pass
        # We got a one in a million chance 100 times in a row. Something is up.
        assert False  # pragma: no cover
    return int_from_bytes(data.draw_bytes(n_bytes, distribution))


def boolean(data):
    return bool(n_byte_unsigned(data, 1) & 1)


def biased_coin(data, p):
    def distribution(random, n):
        assert n == 1
        return hbytes([int(random.random() <= p)])
    return bool(
        data.draw_bytes(1, distribution)[0] & 1
    )


def write(data, string):
    assert isinstance(string, hbytes)

    def distribution(random, n):
        assert n == len(string)
        return string
    x = data.draw_bytes(len(string), distribution)
    if x != string:
        data.mark_invalid()
