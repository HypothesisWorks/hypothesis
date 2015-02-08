# coding=utf-8

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function, unicode_literals, division

# END HEADER

import hypothesis.descriptors as descriptors
import pytest


def test_errors_on_empty_one_of():
    with pytest.raises(ValueError):
        descriptors.one_of([])


def test_returns_just_a_single_element():
    assert descriptors.one_of([1]) == 1
