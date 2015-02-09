# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, unicode_literals

from collections import namedtuple

Just = namedtuple('Just', 'value')
just = Just


OneOf = namedtuple('OneOf', 'elements')


def one_of(args):
    args = tuple(args)
    if not args:
        raise ValueError('one_of requires at least one value to choose from')
    if len(args) == 1:
        return args[0]
    return OneOf(args)


IntegerRange = namedtuple('IntegerRange', ('start', 'end'))


def integers_in_range(start, end):
    return IntegerRange(start, end)


FloatRange = namedtuple('FloatRange', ('start', 'end'))


def floats_in_range(start, end):
    return FloatRange(start, end)


SampledFrom = namedtuple('SampledFrom', ('elements,'))


def sampled_from(elements):
    return SampledFrom(tuple(elements))
