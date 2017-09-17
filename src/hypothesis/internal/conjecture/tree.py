# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

from array import array

from hypothesis.internal.compat import hbytes, hrange
from hypothesis.internal.conjecture.data import Status, ConjectureData


class Node(object):
    def __contains__(self, key):
        try:
            self[key]
            return True
        except KeyError:
            return False


class EmptyNode(Node):
    __slots__ = ('payload',)

    def __getitem__(self, key):
        raise KeyError()

    def __setitem__(self, key, value):
        self.payload = (key, value)
        self.__class__ = SingleNode

    def __len__(self):
        return 0

    def values(self):
        return ()


class SingleNode(Node):
    __slots__ = ('payload',)

    def __getitem__(self, key):
        if key != self.payload[0]:
            raise KeyError()
        return self.payload[1]

    def __setitem__(self, key, value):
        self.payload = {
            key: value, self.payload[0]: self.payload[1]
        }
        self.__class__ = DictNode

    def __len__(self):
        return 1

    def values(self):
        return (self.payload[1],)


class DictNode(Node):
    __slots__ = ('payload',)

    def __getitem__(self, key):
        return self.payload[key]

    def __setitem__(self, key, value):
        self.payload[key] = value

    def __len__(self):
        return len(self.payload)

    def values(self):
        return self.payload.values()


class LanguageCache(object):
    def __init__(self):
        # Tree nodes are stored in an array to prevent heavy nesting of data
        # structures. Branches are dicts mapping bytes to child nodes (which
        # will in general only be partially populated). Leaves are
        # ConjectureData objects that have been previously seen as the result
        # of following that path.
        self.tree = [EmptyNode()]

        # A node is dead if there is nothing left to explore past that point.
        # Recursively, a node is dead if either it is a leaf or every byte
        # leads to a dead node when starting from here.
        self.dead = set()

        # We rewrite the byte stream at various points during parsing, to one
        # that will produce an equivalent result but is in some sense more
        # canonical. We keep track of these so that when walking the tree we
        # can identify nodes where the exact byte value doesn't matter and
        # treat all bytes there as equivalent. This significantly reduces the
        # size of the search space and removes a lot of redundant examples.

        # Maps tree indices where to the unique byte that is valid at that
        # point. Corresponds to data.write() calls.
        self.forced = {}

        # Maps tree indices to the maximum byte that is valid at that point.
        # Currently this is only used inside draw_bits, but it potentially
        # could get used elsewhere.
        self.capped = {}

        # Where a tree node consists of the beginning of a block we track the
        # size of said block. This allows us to tell when an example is too
        # short even if it goes off the unexplored region of the tree - if it
        # is at the beginning of a block of size 4 but only has 3 bytes left,
        # it's going to overrun the end of the buffer regardless of the
        # buffer contents.
        self.block_sizes = {}

    def __is_dead(self, node_index):
        return node_index in self.dead

    def __mark_dead(self, node_index):
        self.dead.add(node_index)

    def add(self, data):
        tree_node = self.tree[0]
        indices = []
        node_index = 0
        for i, b in enumerate(data.buffer):
            indices.append(node_index)
            if i in data.forced_indices:
                self.forced[node_index] = b
            try:
                self.capped[node_index] = data.capped_indices[i]
            except KeyError:
                pass
            try:
                node_index = tree_node[b]
            except KeyError:
                old_node_index = node_index
                node_index = len(self.tree)
                self.tree.append(EmptyNode())
                tree_node[b] = node_index
                if isinstance(tree_node, DictNode):
                    tree_node = self.tree[old_node_index] = tree_node.payload
                if len(tree_node) == 256:
                    tree_node = self.tree[old_node_index] = array('I', [
                        tree_node[c] for c in hrange(256)
                    ])
            tree_node = self.tree[node_index]
            if self.__is_dead(node_index):
                break

        # We don't use this after this point so we might as well get rid of it
        # to save some memory.
        del data.capped_indices

        for u, v in data.blocks:
            # This can happen if we hit a dead node when walking the buffer.
            # In that case we alrady have this section of the tree mapped.
            if u >= len(indices):
                break
            self.block_sizes[indices[u]] = v - u

        if data.status != Status.OVERRUN and not self.__is_dead(node_index):
            self.__mark_dead(node_index)
            self.tree[node_index] = data

            for j in reversed(indices):
                if (
                    len(self.tree[j]) < self.capped.get(j, 255) + 1 and
                    j not in self.forced
                ):
                    break
                jnode = self.tree[j]
                if len(jnode) == 256:
                    values = jnode
                else:
                    values = jnode.values()
                if all(self.__is_dead(v) for v in values):
                    self.__mark_dead(j)
                else:
                    break

    def prescreen_buffer(self, buffer):
        """Attempt to rule out buffer as a possible interesting candidate.

        Returns False if we know for sure that running this buffer will not
        produce an interesting result. Returns True if it might (because it
        explores territory we have not previously tried).

        This is purely an optimisation to try to reduce the number of tests we
        run. "return True" would be a valid but inefficient implementation.

        """
        node_index = 0
        n = len(buffer)
        for k, b in enumerate(buffer):
            if self.__is_dead(node_index):
                return False
            try:
                # The block size at that point provides a lower bound on how
                # many more bytes are required. If the buffer does not have
                # enough bytes to fulfill that block size then we can rule out
                # this buffer.
                if k + self.block_sizes[node_index] > n:
                    return False
            except KeyError:
                pass
            try:
                b = self.forced[node_index]
            except KeyError:
                pass
            try:
                b = min(b, self.capped[node_index])
            except KeyError:
                pass
            try:
                node_index = self.tree[node_index][b]
            except KeyError:
                return True
        else:
            return False

    def rewrite_for_novelty(self, data, result):
        """Take a block that is about to be added to data as the result of a
        draw_bytes call and rewrite it a small amount to ensure that the result
        will be novel: that is, not hit a part of the tree that we have fully
        explored.

        This is mostly useful for test functions which draw a small
        number of blocks.

        """
        assert isinstance(result, hbytes)
        try:
            node_index = data.current_node_index
        except AttributeError:
            node_index = 0
            data.current_node_index = node_index
            data.hit_novelty = False
            data.evaluated_to = 0

        if data.hit_novelty:
            return result

        node = self.tree[node_index]

        for i in hrange(data.evaluated_to, len(data.buffer)):
            node = self.tree[node_index]
            try:
                node_index = node[data.buffer[i]]
                assert self.__is_dead(node_index)
                node = self.tree[node_index]
            except KeyError:
                data.hit_novelty = True
                return result

        for i, b in enumerate(result):
            assert isinstance(b, int)
            try:
                new_node_index = node[b]
            except KeyError:
                data.hit_novelty = True
                return result

            new_node = self.tree[new_node_index]

            if self.__is_dead(new_node_index):
                if isinstance(result, hbytes):
                    result = bytearray(result)
                for c in range(256):
                    if not (len(node) == 256 or c in node):
                        assert c <= self.capped.get(node_index, c)
                        result[i] = c
                        data.hit_novelty = True
                        return hbytes(result)
                    else:
                        new_node_index = node[c]
                        new_node = self.tree[new_node_index]
                        if not self.__is_dead(new_node_index):
                            result[i] = c
                            break
                else:  # pragma: no cover
                    assert False, (
                        'Found a tree node which is live despite all its '
                        'children being dead.')
            node_index = new_node_index
            node = new_node
        assert not self.__is_dead(node_index)
        data.current_node_index = node_index
        data.evaluated_to = data.index + len(result)
        return hbytes(result)

    def cached_answer(self, initial_attempt):
        node_index = 0
        for c in initial_attempt:
            try:
                node_index = self.tree[node_index][c]
            except KeyError:
                break
            node = self.tree[node_index]
            if isinstance(node, ConjectureData):
                return node

    def tree_is_exhausted(self):
        return self.__is_dead(0)
