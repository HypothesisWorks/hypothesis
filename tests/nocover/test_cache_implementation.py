# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from collections import Counter

from hypothesis import strategies as st
from hypothesis.internal.cache import GenericCache
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    initialize,
    invariant,
    rule,
)


class CacheWithScores(GenericCache):
    def __init__(self, max_size):
        super().__init__(max_size)
        self.scores = {}

    def new_entry(self, key, value):
        return self.scores[key]


class CacheRules(RuleBasedStateMachine):
    keys = Bundle("keys")

    @initialize(max_size=st.integers(1, 8))
    def create_cache(self, max_size):
        self.cache = CacheWithScores(max_size)
        self.__values = {}

        self.__total_pins = 0
        self.__pins = Counter()
        self.__live = set()
        self.__next_value = 0
        self.__last_key = None

        def on_evict(evicted_key, value, score):
            assert self.__pins[evicted_key] == 0
            assert score == self.cache.scores[evicted_key]
            assert value == self.__values[evicted_key]
            for k in self.cache:
                assert (
                    self.__pins[k] > 0
                    or self.cache.scores[k] >= score
                    or k == self.__last_key
                )

        self.cache.on_evict = on_evict

    @rule(key=st.integers(), score=st.integers(0, 100), target=keys)
    def new_key(self, key, score):
        if key not in self.cache.scores:
            self.cache.scores[key] = score
        return key

    @rule(key=keys)
    def set_key(self, key):
        if self.__total_pins < self.cache.max_size or key in self.cache:
            self.__last_key = key
            self.cache[key] = self.__next_value
            self.__values[key] = self.__next_value
            self.__next_value += 1

    @invariant()
    def check_values(self):
        self.cache.check_valid()
        for key in self.cache:
            assert self.__values[key] == self.cache[key]

    @rule(key=keys)
    def pin_key(self, key):
        if key in self.cache:
            self.cache.pin(key, self.__values[key])
            if self.__pins[key] == 0:
                self.__total_pins += 1
            self.__pins[key] += 1

    @rule(key=keys)
    def unpin_key(self, key):
        if self.__pins[key] > 0:
            self.cache.unpin(key)
            self.__pins[key] -= 1
            if self.__pins[key] == 0:
                self.__total_pins -= 1
                assert self.__total_pins >= 0


TestCache = CacheRules.TestCase
