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

from math import sqrt, isnan, isinf, fabs
from sys import float_info as fi

def cathetus(h, a):
    """Given the lengths of the hypotenuse and a side of a right
    triangle, return the length of the other side.  A companion
    to the C99 hypot() function.
    https://github.com/jjgreen/cathetus
    """
    if isnan(h):
        return float(u'nan')

    if isinf(h):
        if isinf(a):
            return float(u'nan')
        else:
            return float(u'inf')

    h = fabs(h)
    a = fabs(a)

    if h < a:
        return float(u'nan')

    if h > sqrt(fi.max):
        if h > fi.max / 2:
            return sqrt(h - a) * sqrt(h/2 + a/2) * sqrt(2)
        else:
            return sqrt(h - a) * sqrt(h + a)

    if h < sqrt(fi.min):
        return sqrt(h - a) * sqrt(h + a)

    return sqrt((h - a) * (h + a))
