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

import math
import struct

from hypothesis.internal.compat import CAN_PACK_HALF_FLOAT, quiet_raise, \
    struct_pack, struct_unpack

try:
    import numpy
except ImportError:
    numpy = None


STRUCT_FORMATS = {
    16: (b'!H', b'!e'),  # Note: 'e' is new in Python 3.6, so we have helpers
    32: (b'!I', b'!f'),
    64: (b'!Q', b'!d'),
}


def reinterpret_bits(x, from_, to):
    try:
        buf = struct_pack(from_, x)
    except struct.error:  # pragma: no cover
        if from_ == b'!e' and numpy is not None and not CAN_PACK_HALF_FLOAT:
            arr = numpy.array([x], dtype='>f2')
            if numpy.isfinite(x) and not numpy.isfinite(arr[0]):
                quiet_raise(OverflowError(
                    'value=%r is unrepresentable as float16' % (x,)
                ))
            buf = arr.tobytes()
        else:
            raise
    try:
        return struct_unpack(to, buf)[0]
    except struct.error:  # pragma: no cover
        if to == b'!e' and numpy is not None and not CAN_PACK_HALF_FLOAT:
            return float(numpy.frombuffer(buf, dtype='>f2')[0])
        raise


def float_of(x, width):
    assert width in (16, 32, 64)
    if width == 64:
        return float(x)
    elif width == 32:
        return reinterpret_bits(float(x), b'!f', b'!f')
    else:
        return reinterpret_bits(float(x), b'!e', b'!e')


def sign(x):
    try:
        return math.copysign(1.0, x)
    except TypeError:
        raise TypeError('Expected float but got %r of type %s' % (
            x, type(x).__name__
        ))


def is_negative(x):
    return sign(x) < 0


def count_between_floats(x, y, width=64):
    assert x <= y
    if is_negative(x):
        if is_negative(y):
            return float_to_int(x, width) - float_to_int(y, width) + 1
        else:
            return count_between_floats(x, -0.0, width) + \
                count_between_floats(0.0, y, width)
    else:
        assert not is_negative(y)
        return float_to_int(y, width) - float_to_int(x, width) + 1


def float_to_int(value, width=64):
    fmt_int, fmt_flt = STRUCT_FORMATS[width]
    return reinterpret_bits(value, fmt_flt, fmt_int)


def int_to_float(value, width=64):
    fmt_int, fmt_flt = STRUCT_FORMATS[width]
    return reinterpret_bits(value, fmt_int, fmt_flt)


def next_up(value, width=64):
    """Return the first float larger than finite `val` - IEEE 754's `nextUp`.

    From https://stackoverflow.com/a/10426033, with thanks to Mark Dickinson.
    """
    assert isinstance(value, float)
    if math.isnan(value) or (math.isinf(value) and value > 0):
        return value
    if value == 0.0:
        value = 0.0
    fmt_int, fmt_flt = STRUCT_FORMATS[width]
    # Note: n is signed; float_to_int returns unsigned
    fmt_int = fmt_int.lower()
    n = reinterpret_bits(value, fmt_flt, fmt_int)
    if n >= 0:
        n += 1
    else:
        n -= 1
    return reinterpret_bits(n, fmt_int, fmt_flt)


def next_down(value, width=64):
    return -next_up(-value, width)
