# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

import attr

import hypothesis.strategies as st
from hypothesis import given, settings
from hypothesis.internal.compat import hrange
from hypothesis.internal.conjecture.data import Status
from hypothesis.internal.conjecture.engine import TargetSelector, universal


@attr.s()
class FakeConjectureData(object):
    tags = attr.ib()

    @property
    def status(self):
        return Status.VALID


@st.composite
def fake_randoms(draw):
    data = draw(st.data())

    class FakeRandom(object):
        def choice(self, values):
            if len(values) == 1:
                return values[0]
            return data.draw(st.sampled_from(values), label='choice(%r)' % (
                values,))
    return FakeRandom()


@settings(deadline=None)
@given(fake_randoms())
def test_selects_non_universal_tag(rnd):
    selector = TargetSelector(rnd)
    selector.add(FakeConjectureData({0}))
    selector.add(FakeConjectureData(set()))
    tag1, x = selector.select()
    assert tag1 is not universal
    tag2, y = selector.select()
    assert tag2 is not universal
    assert tag1 != tag2
    assert x != y


data_lists = st.lists(
    st.builds(FakeConjectureData, st.frozensets(st.integers(0, 10))),
    min_size=1)


def check_bounded_cycle(selector):
    everything = selector.examples_by_tags[universal]
    tags = frozenset()
    for d in everything:
        tags |= d.tags
    for _ in hrange(2 * len(tags) + 1):
        t, x = selector.select()
        tags -= x.tags
        if not tags:
            break
    assert not tags


@settings(use_coverage=False, deadline=None)
@given(fake_randoms(), data_lists)
def test_cycles_through_all_tags_in_bounded_time(rnd, datas):
    selector = TargetSelector(rnd)
    for d in datas:
        selector.add(d)
    check_bounded_cycle(selector)


@settings(use_coverage=False, deadline=None)
@given(fake_randoms(), data_lists, data_lists)
def test_cycles_through_all_tags_in_bounded_time_mixed(rnd, d1, d2):
    selector = TargetSelector(rnd)
    for d in d1:
        selector.add(d)
    check_bounded_cycle(selector)
    for d in d2:
        selector.add(d)
    check_bounded_cycle(selector)


@settings(deadline=None)
@given(fake_randoms())
def test_a_negated_tag_is_also_interesting(rnd):
    selector = TargetSelector(rnd)
    selector.add(FakeConjectureData(tags=frozenset({0})))
    selector.add(FakeConjectureData(tags=frozenset({0})))
    selector.add(FakeConjectureData(tags=frozenset()))
    _, data = selector.select()
    assert not data.tags


@settings(deadline=None)
@given(fake_randoms(), st.integers(1, 10))
def test_always_starts_with_rare_tags(rnd, n):
    selector = TargetSelector(rnd)
    selector.add(FakeConjectureData(tags=frozenset({0})))
    for _ in hrange(n):
        selector.select()
    selector.add(FakeConjectureData(tags=frozenset({1})))
    _, data = selector.select()
    assert 1 in data.tags
