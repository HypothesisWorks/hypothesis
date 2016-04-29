# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
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

from hypothesis.internal.compat import hbytes
from hypothesis.internal.conjecture.minimizer import minimize


def test_shrink_to_zero():
    assert minimize(hbytes([255] * 8), lambda x: True) == hbytes(8)


def test_shrink_to_smallest():
    assert minimize(
        hbytes([255] * 8), lambda x: sum(x) > 10
    ) == hbytes([0] * 7 + [11])
