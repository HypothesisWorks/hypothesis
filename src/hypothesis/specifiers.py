# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

import math
from collections import namedtuple

from hypothesis.errors import InvalidArgument
from hypothesis.internal.compat import text_type

Just = namedtuple(u'Just', u'value')
just = Just


OneOf = namedtuple(u'OneOf', u'elements')


def one_of(args):
    args = tuple(args)
    if not args:
        raise ValueError(u'one_of requires at least one value to choose from')
    if len(args) == 1:
        return args[0]
    return OneOf(args)


IntegersFrom = namedtuple(u'IntegersFrom', (u'lower_bound',))

integers_from = IntegersFrom
positive_integers = IntegersFrom(0)

IntegerRange = namedtuple(u'IntegerRange', (u'start', u'end'))


def integers_in_range(start, end):
    return IntegerRange(start, end)


FloatRange = namedtuple(u'FloatRange', (u'start', u'end'))


def floats_in_range(start, end):
    for t in (start, end):
        if math.isinf(t) or math.isnan(t):
            raise InvalidArgument(u'Invalid range: %r, %r' % (start, end,))
    if end < start:
        raise InvalidArgument(
            u'Invalid range: end=%f < start=%f' % (end, start))

    return FloatRange(start, end)


SampledFrom = namedtuple(u'SampledFrom', (u'elements,'))


def sampled_from(elements):
    return SampledFrom(tuple(elements))


Dictionary = namedtuple(u'Dictionary', (u'keys', u'values', u'dict_class'))


def dictionary(keys, values, dict_class=dict):
    return Dictionary(keys, values, dict_class)


Streaming = namedtuple(u'Streaming', (u'data',))

streaming = Streaming


Strings = namedtuple(u'Strings', (u'alphabet',))


def strings(alphabet):
    return Strings(text_type(alphabet))
