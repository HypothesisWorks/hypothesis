# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pytest
from hypothesis import Settings, strategy
from tests.common.utils import capture_out
from hypothesis.specifiers import just, sampled_from, integers_in_range
from hypothesis.experimental.stateful import GenericStateMachine


class SetStateMachine(GenericStateMachine):

    def __init__(self):
        self.elements = []

    def steps(self):
        strat = strategy((just(False), int))
        if self.elements:
            strat |= strategy((just(True), sampled_from(self.elements)))
        return strat

    def execute_step(self, step):
        delete, value = step
        if delete:
            self.elements.remove(value)
            assert value not in self.elements
        else:
            self.elements.append(value)


class OrderedStateMachine(GenericStateMachine):

    def __init__(self):
        self.counter = 0

    def steps(self):
        return strategy(
            integers_in_range(self.counter - 1, self.counter + 50)
        )

    def execute_step(self, step):
        assert step >= self.counter
        self.counter = step


class GoodSet(GenericStateMachine):

    def __init__(self):
        self.stuff = set()

    def steps(self):
        return strategy(bool)

    def execute_step(self, step):
        pass


bad_machines = (OrderedStateMachine, SetStateMachine)


@pytest.mark.parametrize(
    'machine',
    bad_machines, ids=[t.__name__ for t in bad_machines]
)
def test_bad_machines_fail(machine):
    test_class = machine.to_test_case()
    with capture_out() as o:
        with pytest.raises(AssertionError):
            test_class().runTest()
    v = o.getvalue()
    assert 'Step #1' in v
    assert 'Step #9' not in v


def test_good_machine_does_not_fail():
    with Settings(max_examples=50):
        GoodSet.to_test_case()().runTest()
