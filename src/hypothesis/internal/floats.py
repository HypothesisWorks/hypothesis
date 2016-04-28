# coding=utf-8
#
# This file is part of Hypothesis
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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
import struct


def sign(x):
    try:
        return math.copysign(1.0, x)
    except TypeError:
        raise TypeError('Expected float but got %r of type %s' % (
            x, type(x).__name__
        ))


def is_negative(x):
    return sign(x) < 0


def count_between_floats(x, y):
    assert x <= y
    if is_negative(x):
        if is_negative(y):
            return float_to_int(x) - float_to_int(y) + 1
        else:
            return count_between_floats(x, -0.0) + count_between_floats(0.0, y)
    else:
        assert not is_negative(y)
        return float_to_int(y) - float_to_int(x) + 1


def float_to_int(value):
    return (
        struct.unpack(b'!Q', struct.pack(b'!d', value))[0]
    )


def int_to_float(value):
    return (
        struct.unpack(b'!d', struct.pack(b'!Q', value))[0]
    )
