# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

from random import Random

import pytest

from hypothesis import find, given, Settings
from hypothesis.errors import InvalidArgument
from hypothesis.strategies import sets, lists, floats, randoms, booleans, \
    integers, frozensets


def test_template_equality():
    s = sets(integers())
    t = s.draw_and_produce(Random(1))
    assert t != 1

    t2 = s.draw_and_produce(Random(1))
    assert t is not t2
    assert t == t2
    s.reify(t2)
    assert t == t2
    assert hash(t) == hash(t2)

    t3 = s.draw_and_produce(Random(1))
    s.reify(t3)
    for ts in s.full_simplify(Random(1), t3):
        assert t3 != ts


def test_simplifying_unreified_template_does_not_error():
    s = sets(integers())
    t = s.draw_and_produce(Random(1))
    list(s.full_simplify(Random(1), t))


def test_reified_templates_are_simpler():
    s = sets(integers())
    t1 = s.draw_and_produce(Random(1))
    t2 = s.draw_and_produce(Random(1))

    assert t1 == t2
    assert not s.strictly_simpler(t1, t2)

    s.reify(t1)
    assert s.strictly_simpler(t1, t2)
    assert not s.strictly_simpler(t2, t1)


def test_simplify_does_not_error_on_unreified_data():
    s = sets(integers())
    for i in range(100):
        t1 = s.draw_and_produce(Random(i))
        t2 = s.draw_and_produce(Random(i))
        if t1.size > 1:
            break

    s.reify(t1)
    simplifiers = list(s.simplifiers(Random(1), t1))
    assert len(simplifiers) > 2
    for s in simplifiers:
        assert list(s(Random(1), t2)) == []


def test_can_clone_same_length_items():
    ls = find(
        lists(frozensets(integers(), min_size=10, max_size=10)),
        lambda x: len(x) >= 20
    )
    assert len(set(ls)) == 1


def test_unique_lists_error_on_too_large_average_size():
    with pytest.raises(InvalidArgument):
        lists(integers(), unique=True, average_size=10, max_size=5).example()


@given(randoms())
def test_templates_reify_to_same_value_before_and_after(rnd):
    s = sets(booleans())
    t = s.draw_and_produce(rnd)
    t2 = s.from_basic(s.to_basic(t))
    assert s.reify(t) == s.reify(t2)


@given(randoms(), settings=Settings(max_examples=5))
def test_can_draw_sets_of_hard_to_find_elements(rnd):
    rarebool = floats(0, 1).map(lambda x: x <= 0.01)
    find(
        sets(rarebool, min_size=2), lambda x: True,
        random=rnd, settings=Settings(database=None))
