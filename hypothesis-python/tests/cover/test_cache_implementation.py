# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import threading
from functools import partial
from random import Random

import pytest

from hypothesis import (
    HealthCheck,
    assume,
    example,
    given,
    note,
    settings,
    strategies as st,
)
from hypothesis.errors import InvalidArgument
from hypothesis.internal.cache import GenericCache, LRUCache, LRUReusedCache

from tests.common.utils import skipif_emscripten


class LRUCacheAlternative(GenericCache):
    __slots__ = ("__tick",)

    def __init__(self, max_size):
        super().__init__(max_size)
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
def write_pattern(draw, min_distinct_keys=0):
    keys = draw(
        st.lists(st.integers(0, 1000), unique=True, min_size=max(min_distinct_keys, 1))
    )
    values = draw(st.lists(st.integers(), unique=True, min_size=1))
    s = st.lists(
        st.tuples(st.sampled_from(keys), st.sampled_from(values)),
        min_size=min_distinct_keys,
    )
    if min_distinct_keys > 0:
        s = s.filter(lambda ls: len({k for k, _ in ls}) >= min_distinct_keys)
    return draw(s)


class ValueScored(GenericCache):
    def new_entry(self, key, value):
        return value


class RandomCache(GenericCache):
    def __init__(self, max_size):
        super().__init__(max_size)
        self.random = Random(0)

    def new_entry(self, key, value):
        return self.random.random()

    def on_access(self, key, value, score):
        return self.random.random()


@pytest.mark.parametrize(
    "implementation",
    [LRUCache, LFUCache, LRUReusedCache, ValueScored, RandomCache, LRUCacheAlternative],
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


@settings(
    suppress_health_check={HealthCheck.too_slow}
    | set(settings.get_profile(settings._current_profile).suppress_health_check),
    deadline=None,
)
@given(write_pattern(min_distinct_keys=2), st.data())
def test_always_evicts_the_lowest_scoring_value(writes, data):
    scores = {}

    n_keys = len({k for k, _ in writes})

    assume(n_keys > 1)

    size = data.draw(st.integers(1, n_keys - 1))

    evicted = set()

    def new_score(key):
        scores[key] = data.draw(st.integers(0, 1000), label=f"scores[{key!r}]")
        return scores[key]

    last_entry = None

    class Cache(GenericCache):
        def new_entry(self, key, value):
            nonlocal last_entry
            last_entry = key
            evicted.discard(key)
            assert key not in scores
            return new_score(key)

        def on_access(self, key, value, score):
            assert key in scores
            return new_score(key)

        def on_evict(self, key, value, score):
            note(f"Evicted {key!r}")
            assert score == scores[key]
            del scores[key]
            if len(scores) > 1:
                assert score <= min(v for k, v in scores.items() if k != last_entry)
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


def test_max_size_must_be_positive():
    with pytest.raises(InvalidArgument):
        ValueScored(max_size=0)


def test_pinning_prevents_eviction():
    cache = LRUReusedCache(max_size=10)
    cache.pin(20, 1)
    for i in range(20):
        cache[i] = 0
    assert cache[20] == 1


def test_unpinning_allows_eviction():
    cache = LRUReusedCache(max_size=10)
    cache.pin(20, True)
    for i in range(20):
        cache[i] = False

    assert 20 in cache

    cache.unpin(20)
    cache[21] = False

    assert 20 not in cache


def test_unpins_must_match_pins():
    cache = LRUReusedCache(max_size=2)
    cache.pin(1, 1)
    assert cache.is_pinned(1)
    assert cache[1] == 1
    cache.pin(1, 2)
    assert cache.is_pinned(1)
    assert cache[1] == 2
    cache.unpin(1)
    assert cache.is_pinned(1)
    assert cache[1] == 2
    cache.unpin(1)
    assert not cache.is_pinned(1)


def test_will_error_instead_of_evicting_pin():
    cache = LRUReusedCache(max_size=1)
    cache.pin(1, 1)
    with pytest.raises(ValueError):
        cache[2] = 2

    assert 1 in cache
    assert 2 not in cache


def test_will_error_for_bad_unpin():
    cache = LRUReusedCache(max_size=1)
    cache[1] = 1
    with pytest.raises(ValueError):
        cache.unpin(1)


def test_still_inserts_if_score_is_worse():
    class TC(GenericCache):
        def new_entry(self, key, value):
            return key

    cache = TC(1)

    cache[0] = 1
    cache[1] = 1

    assert 0 not in cache
    assert 1 in cache
    assert len(cache) == 1


def test_does_insert_if_score_is_better():
    class TC(GenericCache):
        def new_entry(self, key, value):
            return value

    cache = TC(1)

    cache[0] = 1
    cache[1] = 0

    assert 0 not in cache
    assert 1 in cache
    assert len(cache) == 1


def test_double_pinning_does_not_add_entry():
    cache = LRUReusedCache(2)
    cache.pin(0, 0)
    cache.pin(0, 1)
    cache[1] = 1
    assert len(cache) == 2


def test_can_add_new_keys_after_unpinning():
    cache = LRUReusedCache(1)
    cache.pin(0, 0)
    cache.unpin(0)
    cache[1] = 1
    assert len(cache) == 1
    assert 1 in cache


def test_iterates_over_remaining_keys():
    cache = LRUReusedCache(2)
    for i in range(3):
        cache[i] = "hi"
    assert sorted(cache) == [1, 2]


def test_lru_cache_is_actually_lru():
    cache = LRUCache(2)
    cache[1] = 1  # [1]
    cache[2] = 2  # [1, 2]
    cache[1]  # [2, 1]
    cache[3] = 2  # [2, 1, 3] -> drop least recently used -> [1, 3]
    assert list(cache) == [1, 3]


@skipif_emscripten
def test_cache_is_threadsafe_issue_2433_regression():
    errors = []

    def target():
        for _ in range(1000):
            try:
                st.builds(partial(str))
            except Exception as exc:
                errors.append(exc)

    workers = [threading.Thread(target=target) for _ in range(4)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    assert not errors
