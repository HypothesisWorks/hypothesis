# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pytest
from hypothesis import given, strategy


@pytest.mark.parametrize(('specifier', 'condition'), [
    (int, lambda x: x > 1),
    ([int], bool),
])
def test_filter_correctly(specifier, condition):
    @given(strategy(specifier).filter(condition))
    def test_is_filtered(x):
        assert condition(x)

    test_is_filtered()
