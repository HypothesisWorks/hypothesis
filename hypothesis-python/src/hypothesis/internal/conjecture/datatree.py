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

from collections import defaultdict

import attr

from hypothesis.errors import Flaky
from hypothesis.internal.compat import hbytes, hrange, int_to_bytes
from hypothesis.internal.conjecture.data import (
    ConjectureData,
    Status,
    StopTest,
    bits_to_bytes,
)


class PreviouslyUnseenBehaviour(Exception):
    pass


@attr.s(slots=True)
class PendingNode(object):
    """Mutable wrapper holding a node that records a value (that
    may not have been set yet)"""

    discovered = attr.ib(default=None)

    @property
    def is_exhausted(self):
        if self.discovered is None:
            return False
        return self.discovered.is_exhausted

    def update_exhausted(self):
        pass


@attr.s(slots=True)
class BranchNode(object):
    """Records a place where ``draw_bits`` was called unforced."""

    bits = attr.ib()
    children = attr.ib(default=attr.Factory(lambda: defaultdict(PendingNode)))
    is_exhausted = attr.ib(default=False)

    def child(self, n):
        child = self.children[n]
        if isinstance(child, PendingNode) and child.discovered is not None:
            child = child.discovered
            self.children[n] = child
        return child

    def update_exhausted(self):
        if self.is_exhausted:
            return
        if len(self.children) < 1 << self.bits:
            return
        self.is_exhausted = all(c.is_exhausted for c in self.children.values())


@attr.s(slots=True)
class WriteNode(object):
    """Records a place where ``draw_bits`` was called forced."""

    bits = attr.ib()
    value = attr.ib()
    only_child = attr.ib(default=attr.Factory(PendingNode))

    def child(self, n):
        assert n == self.value
        if (
            isinstance(self.only_child, PendingNode)
            and self.only_child.discovered is not None
        ):
            self.only_child = self.only_child.discovered
        return self.only_child

    @property
    def is_exhausted(self):
        return self.only_child.is_exhausted

    def update_exhausted(self):
        pass


@attr.s(slots=True)
class Conclusion(object):
    status = attr.ib()

    @property
    def is_exhausted(self):
        return True

    def update_exhausted(self):
        pass


CONCLUSIONS = {s: Conclusion(s) for s in Status}


class DataTree(object):
    """Tracks the tree structure of a collection of ConjectureData
    objects, for use in ConjectureRunner."""

    def __init__(self, cap):
        self.cap = cap

        self.root = PendingNode()

    @property
    def is_exhausted(self):
        """Returns True if every possible node is dead and thus the language
        described must have been fully explored."""
        return self.root.is_exhausted

    def __inconsistent_generation(self):
        raise Flaky(
            "Inconsistent data generation! Data generation behaved differently "
            "between different runs. Is your data generation depending on external "
            "state?"
        )

    def __set_conclusion(self, node, status):
        """Says that ``status`` occurred at node ``node``. This updates the
        node if necessary and checks for consistency."""
        existing = None
        if isinstance(node, Conclusion):
            existing = node
        elif isinstance(node, PendingNode):
            if node.discovered is None:
                if status == Status.OVERRUN:
                    return
                node.discovered = CONCLUSIONS[status]
            elif not isinstance(node.discovered, Conclusion):
                self.__inconsistent_generation()
            else:
                existing = node.discovered
        else:  # pragma: no cover
            assert False, "Unexpected node type %s" % (node.__class__.__name__,)
        if existing is not None and existing.status != status:
            raise Flaky(
                "Inconsistent test results! Test case was %s on first run but %s on second"
                % (existing.status.name, status)
            )

    def add(self, data):
        """Add a ConjectureData object to the current collection."""

        current_node = self.root
        trail = [current_node]
        for b, n in data.blocks_with_values():
            is_forced = b.forced or b.start >= self.cap
            if isinstance(current_node, PendingNode):
                if current_node.discovered is None:
                    if is_forced:
                        current_node.discovered = WriteNode(value=n, bits=b.bits)
                    else:
                        current_node.discovered = BranchNode(bits=b.bits)
                current_node = current_node.discovered
                assert not isinstance(current_node, PendingNode)
            if (
                isinstance(current_node, Conclusion)
                or isinstance(current_node, WriteNode) != is_forced
                or current_node.bits != b.bits
                or (isinstance(current_node, WriteNode) and current_node.value != n)
            ):
                self.__inconsistent_generation()
            current_node = current_node.child(n)
            trail.append(current_node)

        self.__set_conclusion(current_node, data.status)

        while trail:
            n = trail.pop()
            n.update_exhausted()
            if not n.is_exhausted:
                break

        if isinstance(self.root, PendingNode) and self.root.discovered is not None:
            self.root = self.root.discovered

    def mask(self, node_index):
        return (1 << self.bit_counts.get(node_index, 8)) - 1

    def generate_novel_prefix(self, random):
        """Generate a short random string that (after rewriting) is not
        a prefix of any buffer previously added to the tree."""
        assert not self.is_exhausted

        node = self.root
        if isinstance(node, PendingNode):
            # We've not explored yet so everything is novel.
            assert node.discovered is None
            return hbytes()

        prefix = bytearray()

        def add_value(v):
            prefix.extend(int_to_bytes(v, bits_to_bytes(node.bits)))

        while True:
            assert not node.is_exhausted
            if isinstance(node, WriteNode):
                add_value(node.value)
                node = node.child(node.value)
            elif isinstance(node, BranchNode):
                while True:
                    v = random.getrandbits(node.bits)
                    next_node = node.child(v)
                    if not next_node.is_exhausted:
                        add_value(v)
                        node = next_node
                        break
            else:
                assert isinstance(node, PendingNode)
                assert node.discovered is None
                break
        return hbytes(prefix)

    def pretend_test_function(self, data):
        """Simulates the behaviour of the test function recorded in this
        tree on data, raising PreviouslyUnseenBehaviour if it ever behaves
        in a way that we do not know the result of.

        Note that currently this method will not call ``start_example`` or
        ``stop_example`` so will only behave correctly on data that does
        not care about the example structure. This will likely change in
        future."""
        node = self.root
        while True:
            if isinstance(node, PendingNode):
                node = node.discovered
                if node is None:
                    raise PreviouslyUnseenBehaviour()
            elif isinstance(node, WriteNode):
                data.draw_bits(node.bits, forced=node.value)
                node = node.child(node.value)
            elif isinstance(node, BranchNode):
                node = node.child(data.draw_bits(node.bits))
            elif isinstance(node, Conclusion):
                data.conclude_test(node.status)
            else:
                assert False

    def rewrite(self, buffer):
        """Use previously seen ConjectureData objects to return a tuple of
        the rewritten buffer and the status we would get from running that
        buffer with the test function. If the status cannot be predicted
        from the existing values it will be None."""

        buffer = hbytes(buffer)

        data = ConjectureData.for_buffer(buffer)

        try:
            self.pretend_test_function(data)
        except PreviouslyUnseenBehaviour:
            return (buffer, None)
        except StopTest:
            pass

        return (data.buffer, data.status)


def _is_simple_mask(mask):
    """A simple mask is ``(2 ** n - 1)`` for some ``n``, so it has the effect
    of keeping the lowest ``n`` bits and discarding the rest.

    A mask in this form can produce any integer between 0 and the mask itself
    (inclusive), and the total number of these values is ``(mask + 1)``.
    """
    return (mask & (mask + 1)) == 0
