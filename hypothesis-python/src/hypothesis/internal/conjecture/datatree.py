# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
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

from __future__ import absolute_import, division, print_function

import attr

from hypothesis.errors import Flaky, HypothesisException
from hypothesis.internal.compat import hbytes
from hypothesis.internal.conjecture.data import DataObserver, Status


class PreviouslyUnseenBehaviour(HypothesisException):
    pass


def inconsistent_generation():
    raise Flaky(
        "Inconsistent data generation! Data generation behaved differently "
        "between different runs. Is your data generation depending on external "
        "state?"
    )


EMPTY = frozenset()


@attr.s(slots=True)
class Branch(object):
    bits = attr.ib()
    children = attr.ib()


@attr.s(slots=True, frozen=True)
class Conclusion(object):
    status = attr.ib()
    interesting_origin = attr.ib()


CONCLUSIONS = {}


def conclusion(status, interesting_origin):
    result = Conclusion(status, interesting_origin)
    return CONCLUSIONS.setdefault(result, result)


@attr.s(slots=True)
class TreeNode(object):
    """Node in a tree that corresponds to previous interactions with
    a ``ConjectureData`` object according to some fixed test function.

    This is functionally a variant patricia trie.
    See https://en.wikipedia.org/wiki/Radix_tree for the general idea,
    but what this means in particular here is that we have a very deep
    but very lightly branching tree and rather than store this as a fully
    recursive structure we flatten prefixes and long branches into
    lists. This significantly compacts the storage requirements.
    """

    # Records the previously drawn bits and their
    # corresponding values. Either len(bits) == len(values)
    # or len(bits) == len(values) + 1 and the last bit call
    # corresponds to the transition to a child node.
    bits = attr.ib(default=attr.Factory(list))
    values = attr.ib(default=attr.Factory(list))

    # The indices of values in the draw list which
    # were forced. None if no indices have been forced,
    # purely for space saving reasons (we force quite rarely).
    __forced = attr.ib(default=None, init=False)

    # Either a dict whose keys are values drawn from
    # bits[-1], or a Status object indicating the test
    # finishes here, or None indicating we don't know
    # what's supposed to be here yet.
    transition = attr.ib(default=None)

    exhausted = attr.ib(default=False, init=False)

    @property
    def forced(self):
        if not self.__forced:
            return EMPTY
        return self.__forced

    def mark_forced(self, i):
        """Note that the value at index ``i`` was forced."""
        assert 0 <= i < len(self.values)
        if self.__forced is None:
            self.__forced = set()
        self.__forced.add(i)

    def split_at(self, i):
        """Splits the tree so that it can incorporate
        a decision at the ``draw_bits`` call corresponding
        to position ``i``, or raises ``Flaky`` if that was
        meant to be a forced node."""

        if i in self.forced:
            inconsistent_generation()

        assert not self.exhausted

        key = self.values[i]

        child = TreeNode(
            bits=self.bits[i + 1 :],
            values=self.values[i + 1 :],
            transition=self.transition,
        )
        self.transition = Branch(bits=self.bits[i], children={key: child})
        if self.__forced is not None:
            child.__forced = {j - i - 1 for j in self.__forced if j > i}
            self.__forced = {j for j in self.__forced if j < i}
        del self.values[i:]
        del self.bits[i:]
        assert len(self.values) == len(self.bits) == i


class DataTree(object):
    """Tracks the tree structure of a collection of ConjectureData
    objects, for use in ConjectureRunner."""

    def __init__(self):
        self.root = TreeNode()

    @property
    def is_exhausted(self):
        """Returns True if every possible node is dead and thus the language
        described must have been fully explored."""
        return False

    def generate_novel_prefix(self, random):
        """Generate a short random string that (after rewriting) is not
        a prefix of any buffer previously added to the tree."""
        return hbytes()

    def rewrite(self, buffer):
        """Use previously seen ConjectureData objects to return a tuple of
        the rewritten buffer and the status we would get from running that
        buffer with the test function. If the status cannot be predicted
        from the existing values it will be None."""
        return (buffer, None)

    def new_observer(self):
        return TreeRecordingObserver(self)


class TreeRecordingObserver(DataObserver):
    def __init__(self, tree):
        self.__current_node = tree.root
        self.__index_in_current_node = 0

    def draw_bits(self, n_bits, forced, value):
        i = self.__index_in_current_node
        self.__index_in_current_node += 1
        node = self.__current_node
        assert len(node.bits) == len(node.values)
        if i < len(node.bits):
            if n_bits != node.bits[i]:
                inconsistent_generation()
            # Note that we don't check whether a previously
            # forced value is now free. That will be caught
            # if we ever split the node there, but otherwise
            # may pass silently. This is acceptable because it
            # means we skip a hash set lookup on every
            # draw and that's a pretty niche failure mode.
            if forced and i not in node.forced:
                inconsistent_generation()
            if value != node.values[i]:
                node.split_at(i)
                assert i == len(node.values)
                new_node = TreeNode()
                branch = node.transition
                branch.children[value] = new_node
                self.__current_node = new_node
                self.__index_in_current_node = 0
        else:
            trans = node.transition
            if trans is None:
                node.bits.append(n_bits)
                node.values.append(value)
                if forced:
                    node.mark_forced(i)
            elif isinstance(trans, Conclusion):
                assert trans.status != Status.OVERRUN
                # We tried to draw where history says we should have
                # stopped
                inconsistent_generation()
            else:
                assert isinstance(trans, Branch)
                if n_bits != trans.bits:
                    inconsistent_generation()
                try:
                    self.__current_node = trans.children[value]
                except KeyError:
                    self.__current_node = trans.children.setdefault(value, TreeNode())
                self.__index_in_current_node = 0

    def conclude_test(self, status, interesting_origin):
        """Says that ``status`` occurred at node ``node``. This updates the
        node if necessary and checks for consistency."""
        if status == Status.OVERRUN:
            return
        i = self.__index_in_current_node
        node = self.__current_node

        if i < len(node.values) or isinstance(node.transition, Branch):
            inconsistent_generation()

        new_transition = conclusion(status, interesting_origin)

        if node.transition is not None and node.transition != new_transition:
            # As an, I'm afraid, horrible bodge, we deliberately ignore flakiness
            # where tests go from interesting to valid, because it's much easier
            # to produce good error messages for these further up the stack.
            if (
                node.transition.status != Status.INTERESTING
                or new_transition.status != Status.VALID
            ):
                raise Flaky(
                    "Inconsistent test results! Test case was %r on first run but %r on second"
                    % (node.transition, new_transition)
                )
        else:
            node.transition = new_transition
