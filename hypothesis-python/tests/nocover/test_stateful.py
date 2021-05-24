# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from collections import namedtuple

import pytest
from pytest import raises

from hypothesis import settings as Settings
from hypothesis.stateful import Bundle, RuleBasedStateMachine, precondition, rule
from hypothesis.strategies import booleans, integers, lists

from tests.common.utils import capture_out

Leaf = namedtuple("Leaf", ("label",))
Split = namedtuple("Split", ("left", "right"))


class BalancedTrees(RuleBasedStateMachine):
    trees = Bundle("BinaryTree")

    @rule(target=trees, x=booleans())
    def leaf(self, x):
        return Leaf(x)

    @rule(target=trees, left=trees, right=trees)
    def split(self, left, right):
        return Split(left, right)

    @rule(tree=trees)
    def test_is_balanced(self, tree):
        if isinstance(tree, Leaf):
            return
        else:
            assert abs(self.size(tree.left) - self.size(tree.right)) <= 1
            self.test_is_balanced(tree.left)
            self.test_is_balanced(tree.right)

    def size(self, tree):
        if isinstance(tree, Leaf):
            return 1
        else:
            return 1 + self.size(tree.left) + self.size(tree.right)


class DepthCharge:
    def __init__(self, value):
        if value is None:
            self.depth = 0
        else:
            self.depth = value.depth + 1


class DepthMachine(RuleBasedStateMachine):
    charges = Bundle("charges")

    @rule(targets=(charges,), child=charges)
    def charge(self, child):
        return DepthCharge(child)

    @rule(targets=(charges,))
    def none_charge(self):
        return DepthCharge(None)

    @rule(check=charges)
    def is_not_too_deep(self, check):
        assert check.depth < 3


class RoseTreeStateMachine(RuleBasedStateMachine):
    nodes = Bundle("nodes")

    @rule(target=nodes, source=lists(nodes))
    def bunch(self, source):
        return source

    @rule(source=nodes)
    def shallow(self, source):
        def d(ls):
            if not ls:
                return 0
            else:
                return 1 + max(map(d, ls))

        assert d(source) <= 5


class NotTheLastMachine(RuleBasedStateMachine):
    stuff = Bundle("stuff")

    def __init__(self):
        super().__init__()
        self.last = None
        self.bye_called = False

    @rule(target=stuff)
    def hi(self):
        result = object()
        self.last = result
        return result

    @precondition(lambda self: not self.bye_called)
    @rule(v=stuff)
    def bye(self, v):
        assert v == self.last
        self.bye_called = True


class PopulateMultipleTargets(RuleBasedStateMachine):
    b1 = Bundle("b1")
    b2 = Bundle("b2")

    @rule(targets=(b1, b2))
    def populate(self):
        return 1

    @rule(x=b1, y=b2)
    def fail(self, x, y):
        assert False


class CanSwarm(RuleBasedStateMachine):
    """This test will essentially never pass if you choose rules uniformly at
    random, because every time the snake rule fires we return to the beginning,
    so we will tend to undo progress well before we make enough progress for
    the test to fail.

    This tests our swarm testing functionality in stateful testing by ensuring
    that we can sometimes generate long runs of steps which exclude a
    particular rule.
    """

    def __init__(self):
        super().__init__()
        self.seen = set()

    # The reason this rule takes a parameter is that it ensures that we do not
    # achieve "swarming" by by just restricting the alphabet for single byte
    # decisions, which is a thing the underlying conjecture engine  will
    # happily do on its own without knowledge of the rule structure.
    @rule(move=integers(0, 255))
    def ladder(self, move):
        self.seen.add(move)
        assert len(self.seen) <= 15

    @rule()
    def snake(self):
        self.seen.clear()


bad_machines = (
    BalancedTrees,
    DepthMachine,
    RoseTreeStateMachine,
    NotTheLastMachine,
    PopulateMultipleTargets,
    CanSwarm,
)

for m in bad_machines:
    m.TestCase.settings = Settings(m.TestCase.settings, max_examples=1000)


cheap_bad_machines = list(bad_machines)
cheap_bad_machines.remove(BalancedTrees)


with_cheap_bad_machines = pytest.mark.parametrize(
    "machine", cheap_bad_machines, ids=[t.__name__ for t in cheap_bad_machines]
)


@pytest.mark.parametrize(
    "machine", bad_machines, ids=[t.__name__ for t in bad_machines]
)
def test_bad_machines_fail(machine):
    test_class = machine.TestCase
    try:
        with capture_out() as o:
            with raises(AssertionError):
                test_class().runTest()
    except Exception:
        print(o.getvalue())
        raise
    v = o.getvalue()
    print(v)
    steps = [l for l in v.splitlines() if "Step " in l or "state." in l]
    assert 1 <= len(steps) <= 50
