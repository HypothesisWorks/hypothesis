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
import time

import pytest

from hypothesis import find, Settings
from hypothesis.errors import Timeout, NoSuchExample, \
    DefinitelyNoSuchExample
from hypothesis.strategies import lists, floats, booleans, integers, \
    streaming, dictionaries


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


def test_find_streaming_int():
    n = 100
    r = find(streaming(integers()), lambda x: all(t >= 1 for t in x[:n]))
    assert list(r[:n]) == [1] * n


def test_raises_when_no_example():
    settings = Settings(
        max_examples=20,
        min_satisfying_examples=0,
    )
    with pytest.raises(NoSuchExample):
        find(integers(), lambda x: False, settings=settings)


def test_raises_more_specifically_when_exhausted():
    with pytest.raises(DefinitelyNoSuchExample):
        find(booleans(), lambda x: False)


def test_condition_is_name():
    settings = Settings(
        max_examples=20,
        min_satisfying_examples=0,
    )
    with pytest.raises(DefinitelyNoSuchExample) as e:
        find(booleans(), lambda x: False, settings=settings)
    assert u'lambda x:' in e.value.args[0]

    with pytest.raises(NoSuchExample) as e:
        find(integers(), lambda x: u'☃' in str(x), settings=settings)
    assert u'lambda x:' in e.value.args[0]

    def bad(x):
        return False

    with pytest.raises(NoSuchExample) as e:
        find(integers(), bad, settings=settings)
    assert u'bad' in e.value.args[0]


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
