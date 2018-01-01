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

import hypothesis.strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule, precondition
from hypothesis.internal.compat import hrange
from tests.cover.test_target_selector import FakeConjectureData, \
    fake_randoms
from hypothesis.internal.conjecture.engine import TargetSelector, universal


class TargetSelectorMachine(RuleBasedStateMachine):
    def __init__(self):
        super(TargetSelectorMachine, self).__init__()
        self.target_selector = None
        self.data = []
        self.tags = set()
        self.tag_intersections = None

    @precondition(lambda self: self.target_selector is None)
    @rule(rnd=fake_randoms())
    def initialize(self, rnd):
        self.target_selector = TargetSelector(rnd)

    @precondition(lambda self: self.target_selector is not None)
    @rule(
        data=st.builds(FakeConjectureData, st.frozensets(st.integers(0, 10))))
    def add_data(self, data):
        self.target_selector.add(data)
        self.data.append(data)
        self.tags.update(data.tags)
        if self.tag_intersections is None:
            self.tag_intersections = data.tags
        else:
            self.tag_intersections &= data.tags

    @precondition(lambda self: self.data)
    @rule()
    def select_target(self):
        tag, data = self.target_selector.select()
        assert self.target_selector.has_tag(tag, data)
        if self.tags != self.tag_intersections:
            assert tag != universal

    @precondition(lambda self: self.data)
    @rule()
    def cycle_through_tags(self):
        seen = set()
        for _ in hrange(
            (2 * len(self.tags) + 1) *
            (1 + self.target_selector.mutation_counts)
        ):
            _, data = self.target_selector.select()
            seen.update(data.tags)
            if seen == self.tags:
                break
        else:
            assert False


TestSelector = TargetSelectorMachine.TestCase
