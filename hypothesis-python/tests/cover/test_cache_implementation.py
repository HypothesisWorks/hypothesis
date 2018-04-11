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

from random import Random

import pytest

import hypothesis.strategies as st
from hypothesis import HealthCheck, note, given, assume, example, settings
from hypothesis.internal.cache import GenericCache, LRUReusedCache


class LRUCache(GenericCache):
    __slots__ = ('__tick',)

    def __init__(self, max_size):
        super(LRUCache, self).__init__(max_size)
        self.__tick = 0

    def new_entry(self, key, value):
        return self.tick()

    def on_access(self, key, value, score):
        return self.tick()

    def tick(self):
        self.__tick += 1
        return self.__tick


class LFUCache(GenericCache):
    def new_entry(self, key, value):
        return 1

    def on_access(self, key, value, score):
        return score + 1


@st.composite
def write_pattern(draw, min_size=0):
    keys = draw(st.lists(st.integers(0, 1000), unique=True, min_size=1))
    values = draw(st.lists(st.integers(), unique=True, min_size=1))
    return draw(
        st.lists(st.tuples(st.sampled_from(keys), st.sampled_from(values)),
                 min_size=min_size))


class ValueScored(GenericCache):
    def new_entry(self, key, value):
        return value


class RandomCache(GenericCache):
    def __init__(self, max_size):
        super(RandomCache, self).__init__(max_size)
        self.random = Random(0)

    def new_entry(self, key, value):
        return self.random.random()

    def on_access(self, key, value, score):
        return self.random.random()


@pytest.mark.parametrize(
    'implementation', [
        LRUCache, LFUCache, LRUReusedCache, ValueScored, RandomCache
    ]
)
@example(writes=[(0, 0), (3, 0), (1, 0), (2, 0), (2, 0), (1, 0)], size=4)
@example(writes=[(0, 0)], size=1)
@example(writes=[(1, 0), (2, 0), (0, -1), (1, 0)], size=3)
@given(write_pattern(), st.integers(1, 10))
def test_behaves_like_a_dict_with_losses(implementation, writes, size):
    model = {}
    target = implementation(max_size=size)

    for k, v in writes:
        try:
            assert model[k] == target[k]
        except KeyError:
            pass
        model[k] = v
        target[k] = v
        target.check_valid()
        assert target[k] == v
        for r, s in model.items():
            try:
                assert s == target[r]
            except KeyError:
                pass
        assert len(target) <= min(len(model), size)


@settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(write_pattern(min_size=2), st.data())
def test_always_evicts_the_lowest_scoring_value(writes, data):
    scores = {}

    n_keys = len({k for k, _ in writes})

    assume(n_keys > 1)

    size = data.draw(st.integers(1, n_keys - 1))

    evicted = set()

    def new_score(key):
        scores[key] = data.draw(
            st.integers(0, 1000), label='scores[%r]' % (key,))
        return scores[key]

    last_entry = [None]

    class Cache(GenericCache):
        def new_entry(self, key, value):
            last_entry[0] = key
            evicted.discard(key)
            assert key not in scores
            return new_score(key)

        def on_access(self, key, value, score):
            assert key in scores
            return new_score(key)

        def on_evict(self, key, value, score):
            note('Evicted %r' % (key,))
            assert score == scores[key]
            del scores[key]
            if len(scores) > 1:
                assert score <= min(
                    v for k, v in scores.items()
                    if k != last_entry[0]
                )
            evicted.add(key)

    target = Cache(max_size=size)
    model = {}

    for k, v in writes:
        target[k] = v
        model[k] = v

    assert evicted
    assert len(evicted) + len(target) == len(model)
    assert len(scores) == len(target)

    for k, v in model.items():
        try:
            assert target[k] == v
            assert k not in evicted
        except KeyError:
            assert k in evicted


def test_basic_access():
    cache = ValueScored(max_size=2)
    cache[1] = 0
    cache[1] = 0
    cache[0] = 1
    cache[2] = 0
    assert cache[2] == 0
    assert cache[0] == 1
    assert len(cache) == 2


def test_can_clear_a_cache():
    x = ValueScored(1)
    x[0] = 1
    assert len(x) == 1
    x.clear()
    assert len(x) == 0


def test_max_size_cache_ignores():
    x = ValueScored(0)
    x[0] = 1
    with pytest.raises(KeyError):
        x[0]
