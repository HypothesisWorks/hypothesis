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
import hypothesis.descriptors as descriptors


def test_errors_on_empty_one_of():
    with pytest.raises(ValueError):
        descriptors.one_of([])


def test_returns_just_a_single_element():
    assert descriptors.one_of([1]) == 1
