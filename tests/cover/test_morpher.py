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

import hypothesis.strategies as s
from flaky import flaky
from hypothesis import find, given, example, settings
from hypothesis.control import BuildContext
from hypothesis.searchstrategy.morphers import MorpherStrategy

morphers = MorpherStrategy()
intlists = s.lists(s.integers())


def test_can_simplify_through_a_morpher():
    m = find(morphers, lambda x: bool(x.become(intlists)))
    assert m.become(intlists) == [0]


@example(Random(187))
@example(Random(0))
@given(s.randoms())
@settings(max_examples=10)
def test_can_simplify_text_through_a_morpher(rnd):
    m = find(
        morphers, lambda x: bool(x.become(s.text())), random=rnd,
        settings=settings(database=None)
    )
    with BuildContext():
        assert m.become(s.text()) == u'0'


def test_can_simplify_lists_of_morphers_of_single_type():
    ms = find(
        s.lists(morphers),
        lambda x: sum(t.become(s.integers()) for t in x) >= 100,
        settings=settings(database=None)
    )

    with BuildContext():
        ls = [t.become(s.integers()) for t in ms]
    assert sum(ls) == 100


def test_can_simplify_through_two_morphers():
    m = find(morphers, lambda x: bool(x.become(morphers).become(intlists)))
    with BuildContext():
        assert m.become(morphers).become(intlists) == [0]


def test_a_morpher_retains_its_data_on_reserializing():
    m = find(morphers, lambda x: sum(x.become(intlists)) > 1)
    m2 = morphers.from_basic(morphers.to_basic(m))
    with BuildContext():
        assert m.become(intlists) == m2.become(intlists)


@flaky(max_runs=5, min_passes=1)
def test_can_clone_morphers_into_inactive_morphers():
    m = find(
        s.lists(morphers),
        lambda x: len(x) >= 2 and x[0].become(s.integers()) >= 0)
    with BuildContext():
        m_as_ints = [x.become(s.integers()) for x in m]
    assert m_as_ints == [0, 0]


def test_thorough_cloning():
    def check(x):
        ids = list(map(id, x))
        assert len(set(ids)) == len(ids)
        return len(x) >= 5 and any(
            m.become(s.integers()) > 0 for m in x)
    r = find(s.lists(morphers), check)
    with BuildContext():
        results = [m.become(s.integers()) for m in r]
    results.sort(key=abs)
    assert results == [0] * 4 + [1]


def test_without_strategies_morphers_synchronize():
    ms = find(
        s.lists(morphers), lambda x: len(x) >= 10
    )
    distinct_ints = set(m.become(s.integers()) for m in ms)
    assert len(distinct_ints) == 1


def test_mixed_type_list():

    def convert_list(ls):
        return [
            v.become(s.booleans())
            for v in ls[:5]
        ] + [
            v.become(s.text())
            for v in ls[5:10]
        ]

    ls = find(
        s.lists(morphers, min_size=15, max_size=15).map(convert_list),
        lambda x: True)
    assert ls[:10] == [False] * 5 + [u''] * 5
