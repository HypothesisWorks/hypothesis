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

import pytest

from hypothesis import given
from hypothesis.strategies import lists, integers


@pytest.mark.parametrize((u'specifier', u'condition'), [
    (integers(), lambda x: x > 1),
    (lists(integers()), bool),
])
def test_filter_correctly(specifier, condition):
    @given(specifier.filter(condition))
    def test_is_filtered(x):
        assert condition(x)

    test_is_filtered()
