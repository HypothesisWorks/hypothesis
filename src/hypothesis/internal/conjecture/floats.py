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

from array import array

from hypothesis.internal.compat import hbytes, hrange, int_to_bytes
from hypothesis.internal.floats import float_to_int, int_to_float

"""
This module implements support for arbitrary floating point numbers in
Conjecture. It doesn't make any attempt to get a good distribution, only to
get a format that will shrink well.

It works by defining an encoding of non-negative floating point numbers
(including NaN values with a zero sign bit) that has good lexical shrinking
properties.

This encoding is a tagged union of two separate encodings for floating point
numbers, with the tag being the first bit of 64 and the remaining 63-bits being
the payload.

If the tag bit is 0, the next 7 bits are ignored, and the remaining 7 bytes are
interpreted as a 7 byte integer in big-endian order and then converted to a
float (there is some redundancy here, as 7 * 8 = 56, which is larger than the
largest integer that floating point numbers can represent exactly, so multiple
encodings may map to the same float).

If the tag bit is 1, we instead use somemthing that is closer to the normal
representation of floats (and can represent every non-negative float exactly)
but has a better ordering:

1. NaNs are ordered after everything else.
2. Infinity is ordered after every finite number.
3. The sign is ignored unless two floating point numbers are identical in
   absolute magnitude. In that case, the positive is ordered before the
   negative.
4. Positive floating point numbers are ordered first by int(x) where
   encoding(x) < encoding(y) if int(x) < int(y).
5. If int(x) == int(y) then x and y are sorted towards lower denominators of
   their fractional parts.

The format of this encoding of floating point goes as follows:

    [exponent] [mantissa]

Each of these is the same size their equivalent in IEEE floating point, but are
in a different format.

We translate exponents as follows:

    1. The maximum exponent (2 ** 11 - 1) is left unchanged.
    2. We reorder the remaining exponents so that all of the positive exponents
       are first, in increasing order, followed by all of the negative
       exponents in decreasing order (where positive/negative is done by the
       unbiased exponent e - 1023).

We translate the mantissa as follows:

    1. If the unbiased exponent is <= 0 we reverse it bitwise.
    2. If the unbiased exponent is >= 52 we leave it alone.
    3. If the unbiased exponent is in the range [1, 51] then we reverse the
       low k bits, where k is 52 - unbiased exponen.

The low bits correspond to the fractional part of the floating point number.
Reversing it bitwise means that we try to minimize the low bits, which kills
off the higher powers of 2 in the fraction first.
"""


MAX_EXPONENT = 0x7ff

SPECIAL_EXPONENTS = (0, MAX_EXPONENT)

BIAS = 1023
MAX_POSITIVE_EXPONENT = (MAX_EXPONENT - 1 - BIAS)


def exponent_key(e):
    if e == MAX_EXPONENT:
        return float('inf')
    unbiased = e - BIAS
    if unbiased < 0:
        return 10000 - unbiased
    else:
        return unbiased


ENCODING_TABLE = array('H', sorted(hrange(MAX_EXPONENT + 1), key=exponent_key))
DECODING_TABLE = array('H', [0]) * len(ENCODING_TABLE)

for i, b in enumerate(ENCODING_TABLE):
    DECODING_TABLE[b] = i

del i, b


def decode_exponent(e):
    """Take draw_bits(11) and turn it into a suitable floating point exponent
    such that lexicographically simpler leads to simpler floats."""
    assert 0 <= e <= MAX_EXPONENT
    return ENCODING_TABLE[e]


def encode_exponent(e):
    """Take a floating point exponent and turn it back into the equivalent
    result from conjecture."""
    assert 0 <= e <= MAX_EXPONENT
    return DECODING_TABLE[e]


# Table mapping individual bytes to the equivalent byte with the bits of the
# byte reversed. e.g. 1=0b1 is mapped to 0xb10000000=0x80=128. We use this
# precalculated table to simplify calculating the bitwise reversal of a longer
# integer.
REVERSE_BITS_TABLE = bytearray([
    0x00, 0x80, 0x40, 0xc0, 0x20, 0xa0, 0x60, 0xe0, 0x10, 0x90, 0x50, 0xd0,
    0x30, 0xb0, 0x70, 0xf0, 0x08, 0x88, 0x48, 0xc8, 0x28, 0xa8, 0x68, 0xe8,
    0x18, 0x98, 0x58, 0xd8, 0x38, 0xb8, 0x78, 0xf8, 0x04, 0x84, 0x44, 0xc4,
    0x24, 0xa4, 0x64, 0xe4, 0x14, 0x94, 0x54, 0xd4, 0x34, 0xb4, 0x74, 0xf4,
    0x0c, 0x8c, 0x4c, 0xcc, 0x2c, 0xac, 0x6c, 0xec, 0x1c, 0x9c, 0x5c, 0xdc,
    0x3c, 0xbc, 0x7c, 0xfc, 0x02, 0x82, 0x42, 0xc2, 0x22, 0xa2, 0x62, 0xe2,
    0x12, 0x92, 0x52, 0xd2, 0x32, 0xb2, 0x72, 0xf2, 0x0a, 0x8a, 0x4a, 0xca,
    0x2a, 0xaa, 0x6a, 0xea, 0x1a, 0x9a, 0x5a, 0xda, 0x3a, 0xba, 0x7a, 0xfa,
    0x06, 0x86, 0x46, 0xc6, 0x26, 0xa6, 0x66, 0xe6, 0x16, 0x96, 0x56, 0xd6,
    0x36, 0xb6, 0x76, 0xf6, 0x0e, 0x8e, 0x4e, 0xce, 0x2e, 0xae, 0x6e, 0xee,
    0x1e, 0x9e, 0x5e, 0xde, 0x3e, 0xbe, 0x7e, 0xfe, 0x01, 0x81, 0x41, 0xc1,
    0x21, 0xa1, 0x61, 0xe1, 0x11, 0x91, 0x51, 0xd1, 0x31, 0xb1, 0x71, 0xf1,
    0x09, 0x89, 0x49, 0xc9, 0x29, 0xa9, 0x69, 0xe9, 0x19, 0x99, 0x59, 0xd9,
    0x39, 0xb9, 0x79, 0xf9, 0x05, 0x85, 0x45, 0xc5, 0x25, 0xa5, 0x65, 0xe5,
    0x15, 0x95, 0x55, 0xd5, 0x35, 0xb5, 0x75, 0xf5, 0x0d, 0x8d, 0x4d, 0xcd,
    0x2d, 0xad, 0x6d, 0xed, 0x1d, 0x9d, 0x5d, 0xdd, 0x3d, 0xbd, 0x7d, 0xfd,
    0x03, 0x83, 0x43, 0xc3, 0x23, 0xa3, 0x63, 0xe3, 0x13, 0x93, 0x53, 0xd3,
    0x33, 0xb3, 0x73, 0xf3, 0x0b, 0x8b, 0x4b, 0xcb, 0x2b, 0xab, 0x6b, 0xeb,
    0x1b, 0x9b, 0x5b, 0xdb, 0x3b, 0xbb, 0x7b, 0xfb, 0x07, 0x87, 0x47, 0xc7,
    0x27, 0xa7, 0x67, 0xe7, 0x17, 0x97, 0x57, 0xd7, 0x37, 0xb7, 0x77, 0xf7,
    0x0f, 0x8f, 0x4f, 0xcf, 0x2f, 0xaf, 0x6f, 0xef, 0x1f, 0x9f, 0x5f, 0xdf,
    0x3f, 0xbf, 0x7f, 0xff,
])

assert len(REVERSE_BITS_TABLE) == 256


def reverse64(v):
    """Reverse a 64-bit integer bitwise.

    We do this by breaking it up into 8 bytes. The 64-bit integer is then the
    concatenation of each of these bytes. We reverse it by reversing each byte
    on its own using the REVERSE_BITS_TABLE above, and then concatenating the
    reversed bytes.

    In this case concatenating consists of shifting them into the right
    position for the word and then oring the bits together.

    """
    assert v.bit_length() <= 64
    return (
        (REVERSE_BITS_TABLE[(v >> 0) & 0xff] << 56) |
        (REVERSE_BITS_TABLE[(v >> 8) & 0xff] << 48) |
        (REVERSE_BITS_TABLE[(v >> 16) & 0xff] << 40) |
        (REVERSE_BITS_TABLE[(v >> 24) & 0xff] << 32) |
        (REVERSE_BITS_TABLE[(v >> 32) & 0xff] << 24) |
        (REVERSE_BITS_TABLE[(v >> 40) & 0xff] << 16) |
        (REVERSE_BITS_TABLE[(v >> 48) & 0xff] << 8) |
        (REVERSE_BITS_TABLE[(v >> 56) & 0xff] << 0)
    )


MANTISSA_MASK = ((1 << 52) - 1)


def reverse_bits(x, n):
    assert x.bit_length() <= n <= 64
    x = reverse64(x)
    x >>= (64 - n)
    return x


def update_mantissa(unbiased_exponent, mantissa):
    if unbiased_exponent <= 0:
        mantissa = reverse_bits(mantissa, 52)
    elif unbiased_exponent <= 51:
        n_fractional_bits = (52 - unbiased_exponent)
        fractional_part = mantissa & ((1 << n_fractional_bits) - 1)
        mantissa ^= fractional_part
        mantissa |= reverse_bits(fractional_part, n_fractional_bits)
    return mantissa


def lex_to_float(i):
    assert i.bit_length() <= 64
    has_fractional_part = i >> 63
    if has_fractional_part:
        exponent = (i >> 52) & ((1 << 11) - 1)
        exponent = decode_exponent(exponent)
        mantissa = i & MANTISSA_MASK
        mantissa = update_mantissa(exponent - BIAS, mantissa)

        assert mantissa.bit_length() <= 52

        return int_to_float((exponent << 52) | mantissa)
    else:
        integral_part = i & ((1 << 56) - 1)
        return float(integral_part)


def float_to_lex(f):
    if is_simple(f):
        assert f >= 0
        return int(f)

    i = float_to_int(f)
    i &= ((1 << 63) - 1)
    exponent = i >> 52
    mantissa = i & MANTISSA_MASK
    mantissa = update_mantissa(exponent - BIAS, mantissa)
    exponent = encode_exponent(exponent)

    assert mantissa.bit_length() <= 52
    return (1 << 63) | (exponent << 52) | mantissa


def is_simple(f):
    try:
        i = int(f)
    except (ValueError, OverflowError):
        return False
    if i != f:
        return False
    return i.bit_length() <= 56


def draw_float(data):
    try:
        data.start_example()
        f = lex_to_float(data.draw_bits(64))
        if data.draw_bits(1):
            f = -f
        return f
    finally:
        data.stop_example()


def write_float(data, f):
    data.write(int_to_bytes(float_to_lex(abs(f)), 8))
    sign = float_to_int(f) >> 63
    data.write(hbytes([sign]))
