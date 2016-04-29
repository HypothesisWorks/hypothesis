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

import math
import time

import pytest

from hypothesis import settings as Settings
from hypothesis import find
from hypothesis.errors import Timeout, NoSuchExample
from hypothesis.strategies import lists, floats, booleans, integers, \
    dictionaries


def test_can_find_an_int():
    assert find(integers(), lambda x: True) == 0
    assert find(integers(), lambda x: x >= 13) == 13


def test_can_find_list():
    x = find(lists(integers()), lambda x: sum(x) >= 10)
    assert sum(x) == 10


def test_can_find_nan():
    find(floats(), math.isnan)


def test_can_find_nans():
    x = find(lists(floats()), lambda x: math.isnan(sum(x)))
    if len(x) == 1:
        assert math.isnan(x[0])
    else:
        assert 2 <= len(x) <= 3


def test_raises_when_no_example():
    settings = Settings(
        max_examples=20,
        min_satisfying_examples=0,
    )
    with pytest.raises(NoSuchExample):
        find(integers(), lambda x: False, settings=settings)


def test_condition_is_name():
    settings = Settings(
        max_examples=20,
        min_satisfying_examples=0,
    )
    with pytest.raises(NoSuchExample) as e:
        find(booleans(), lambda x: False, settings=settings)
    assert 'lambda x:' in e.value.args[0]

    with pytest.raises(NoSuchExample) as e:
        find(integers(), lambda x: '☃' in str(x), settings=settings)
    assert 'lambda x:' in e.value.args[0]

    def bad(x):
        return False

    with pytest.raises(NoSuchExample) as e:
        find(integers(), bad, settings=settings)
    assert 'bad' in e.value.args[0]


def test_find_dictionary():
    assert len(find(
        dictionaries(keys=integers(), values=integers()),
        lambda xs: any(kv[0] > kv[1] for kv in xs.items()))) == 1


def test_times_out():
    with pytest.raises(Timeout) as e:
        find(
            integers(),
            lambda x: time.sleep(0.05) or False,
            settings=Settings(timeout=0.01))

    e.value.args[0]
