# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import math
import struct
from sys import float_info

# Format codes for (int, float) sized types, used for byte-wise casts.
# See https://docs.python.org/3/library/struct.html#format-characters
STRUCT_FORMATS = {
    16: ("!H", "!e"),
    32: ("!I", "!f"),
    64: ("!Q", "!d"),
}


def reinterpret_bits(x, from_, to):
    return struct.unpack(to, struct.pack(from_, x))[0]


def float_of(x, width):
    assert width in (16, 32, 64)
    if width == 64:
        return float(x)
    elif width == 32:
        return reinterpret_bits(float(x), "!f", "!f")
    else:
        return reinterpret_bits(float(x), "!e", "!e")


def sign(x):
    try:
        return math.copysign(1.0, x)
    except TypeError:
        raise TypeError(
            f"Expected float but got {x!r} of type {type(x).__name__}"
        ) from None


def is_negative(x):
    return sign(x) < 0


def count_between_floats(x, y, width=64):
    assert x <= y
    if is_negative(x):
        if is_negative(y):
            return float_to_int(x, width) - float_to_int(y, width) + 1
        else:
            return count_between_floats(x, -0.0, width) + count_between_floats(
                0.0, y, width
            )
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
    assert isinstance(value, float), f"{value!r} of type {type(value)}"
    if math.isnan(value) or (math.isinf(value) and value > 0):
        return value
    if value == 0.0 and is_negative(value):
        return 0.0
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


def next_down_normal(value, width, allow_subnormal):
    value = next_down(value, width)
    if (not allow_subnormal) and 0 < abs(value) < width_smallest_normals[width]:
        return 0.0 if value > 0 else -width_smallest_normals[width]
    return value


def next_up_normal(value, width, allow_subnormal):
    return -next_down_normal(-value, width, allow_subnormal)


# Smallest positive non-zero numbers that is fully representable by an
# IEEE-754 float, calculated with the width's associated minimum exponent.
# Values from https://en.wikipedia.org/wiki/IEEE_754#Basic_and_interchange_formats
width_smallest_normals = {
    16: 2 ** -(2 ** (5 - 1) - 2),
    32: 2 ** -(2 ** (8 - 1) - 2),
    64: 2 ** -(2 ** (11 - 1) - 2),
}
assert width_smallest_normals[64] == float_info.min
