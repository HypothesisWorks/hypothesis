# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

from priority import PriorityMap


def test_insert_one_value():
    x = PriorityMap()
    x[0] = 1
    assert len(x) == 1
    assert x[0] == 1
    x.assert_valid()


def test_delete_only_value():
    x = PriorityMap()
    x[0] = 1
    del x[0]
    assert len(x) == 0
    with pytest.raises(KeyError):
        x[0]
    x.assert_valid()


def test_delete_min_value():
    x = PriorityMap()
    x[0] = 1
    x[1] = 2
    del x[0]
    assert len(x) == 1
    with pytest.raises(KeyError):
        x[0]
    assert x[1] == 2
    x.assert_valid()


def test_delete_last_entry():
    x = PriorityMap()
    x[0] = 0
    x[1] = 1
    del x[1]
    assert len(x) == 1
    with pytest.raises(KeyError):
        x[1]
    assert x[0] == 0
    x.assert_valid()


def test_setting_item_can_change_min():
    x = PriorityMap()
    x[0] = 0
    x[1] = 1
    assert x.peek_min() == (0, 0)
    x[1] = -1
    assert x.peek_min() == (1, -1)
    x.assert_valid()


def test_move_root_under_right_child():
    x = PriorityMap()
    x[0] = 0
    x[2] = 2
    x[1] = 1
    # We now have the heap laid out so the values are (0, 2, 1). This means
    # that when we now change the value of 0 to lie after its children it
    # needs to replace the right child, not the left.
    x[0] = 3
    assert x.peek_min() == (1, 1)
    x.assert_valid()
