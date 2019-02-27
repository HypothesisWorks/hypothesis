# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

"""A module for miscellaneous useful bits and bobs that don't
obviously belong anywhere else. If you spot a better home for
anything that lives here, please move it."""


from __future__ import absolute_import, division, print_function

from hypothesis.internal.compat import array_or_list, hbytes


def replace_all(buffer, replacements):
    """Substitute multiple replacement values into a buffer.

    Replacements is a list of (start, end, value) triples.
    """

    result = bytearray()
    prev = 0
    offset = 0
    for u, v, r in replacements:
        result.extend(buffer[prev:u])
        result.extend(r)
        prev = v
        offset += len(r) - (v - u)
    result.extend(buffer[prev:])
    assert len(result) == len(buffer) + offset
    return hbytes(result)


def calc_bits_to_array_codes():
    """Return a list of the smallest array codes that can be used to
    represent an unsigned integer of size n, for n from 0 to 64 inclusive.
    """
    code_iter = iter(["B", "H", "I", "L", "Q"])
    result = []
    code = next(code_iter)
    while len(result) < 65:
        trial_number = (1 << len(result)) - 1
        assert trial_number.bit_length() == len(result)
        try:
            array_or_list(code, [trial_number])
            result.append(code)
        except OverflowError:
            code = next(code_iter)
    return result


BIT_LENGTH_TO_ARRAY_CODES = calc_bits_to_array_codes()


class IntList(object):
    """Class for storing a list of non-negative integers compactly.

    We store them as the smallest size integer array we can get
    away with. When we try to add an integer that is too large,
    we upgrade the array to the smallest word size needed to store
    the new value."""

    __slots__ = ("__underlying",)

    def __init__(self):
        self.__underlying = array_or_list("B")

    def __len__(self):
        return len(self.__underlying)

    def __getitem__(self, i):
        return self.__underlying[i]

    def __iter__(self):
        return iter(self.__underlying)

    def append(self, n):
        try:
            self.__underlying.append(n)
        except OverflowError:
            self.__underlying = array_or_list(
                BIT_LENGTH_TO_ARRAY_CODES[n.bit_length()], self.__underlying
            )
            self.__underlying.append(n)
