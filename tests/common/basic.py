# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from hypothesis.searchstrategy import BasicStrategy
from hypothesis.internal.compat import hrange


def simplify_bitfield(random, value):
    for i in hrange(128):
        k = 1 << i
        if value & k:
            yield value & (~k)


class BoringBitfields(BasicStrategy):

    def generate(self, random, parameter_value):
        return random.getrandbits(128)


class Bitfields(BasicStrategy):

    def generate_parameter(self, random):
        return random.getrandbits(128)

    def generate(self, random, parameter_value):
        return parameter_value & random.getrandbits(128)

    def simplify(self, random, value):
        return simplify_bitfield(random, value)

    def copy(self, value):
        return value
