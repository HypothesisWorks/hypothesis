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

from hypothesis.internal.compat import hbytes, hrange
from hypothesis.internal.conjecture.data import Status


class DataTree(object):
    """Tracks the tree structure of a collection of ConjectureData
    objects, for use in ConjectureRunner."""

    def __init__(self, cap):
        self.cap = cap

        # Previously-tested byte streams are recorded in a prefix tree, so that
        # we can:
        # - Avoid testing the same stream twice (in some cases).
        # - Avoid testing a prefix of a past stream (in some cases),
        #   since that should only result in overrun.
        # - Generate stream prefixes that we haven't tried before.

        # Tree nodes are stored in an array to prevent heavy nesting of data
        # structures. Branches are dicts mapping bytes to child nodes (which
        # will in general only be partially populated). Leaves are
        # ConjectureData objects that have been previously seen as the result
        # of following that path.
        self.nodes = [{}]

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

        # Maps tree indices to a mask that restricts bytes at that point.
        # Currently this is only updated by draw_bits, but it potentially
        # could get used elsewhere.
        self.masks = {}

        # Where a tree node consists of the beginning of a block we track the
        # size of said block. This allows us to tell when an example is too
        # short even if it goes off the unexplored region of the tree - if it
        # is at the beginning of a block of size 4 but only has 3 bytes left,
        # it's going to overrun the end of the buffer regardless of the
        # buffer contents.
        self.block_sizes = {}

    @property
    def is_exhausted(self):
        """Returns True if every possible node is dead and thus the language
        described must have been fully explored."""
        return 0 in self.dead

    def add(self, data):
        """Add a ConjectureData object to the current collection."""

        # First, iterate through the result's buffer, to create the node that
        # will hold this result. Also note any forced or masked bytes.
        tree_node = self.nodes[0]
        indices = []
        node_index = 0
        for i, b in enumerate(data.buffer):
            # We build a list of all the node indices visited on our path
            # through the tree, since we'll need to refer to them later.
            indices.append(node_index)

            # If this buffer position was forced or masked, then mark its
            # corresponding node as forced/masked.
            if i in data.forced_indices:
                self.forced[node_index] = b
            try:
                self.masks[node_index] = data.masked_indices[i]
            except KeyError:
                pass

            try:
                # Use the current byte to find the next node on our path.
                node_index = tree_node[b]
            except KeyError:
                # That node doesn't exist yet, so create it.
                node_index = len(self.nodes)
                # Create a new branch node. If this should actually be a leaf
                # node, it will be overwritten when we store the result.
                self.nodes.append({})
                tree_node[b] = node_index

            tree_node = self.nodes[node_index]

            if node_index in self.dead:
                # This part of the tree has already been marked as dead, so
                # there's no need to traverse any deeper.
                break

        # At each node that begins a block, record the size of that block.
        for b in data.blocks:
            u, v = b.bounds
            # This can happen if we hit a dead node when walking the buffer.
            # In that case we already have this section of the tree mapped.
            if u >= len(indices):
                break
            self.block_sizes[indices[u]] = v - u

        # Forcibly mark all nodes beyond the zero-bound point as dead,
        # because we don't intend to try any other values there.
        self.dead.update(indices[self.cap :])

        # Now store this result in the tree (if appropriate), and check if
        # any nodes need to be marked as dead.
        if data.status != Status.OVERRUN and node_index not in self.dead:
            # Mark this node as dead, because it produced a result.
            # Trying to explore suffixes of it would not be helpful.
            self.dead.add(node_index)
            # Store the result in the tree as a leaf. This will overwrite the
            # branch node that was created during traversal.
            self.nodes[node_index] = data.status

            # Review the traversed nodes, to see if any should be marked
            # as dead. We check them in reverse order, because as soon as we
            # find a live node, all nodes before it must still be live too.
            for j in reversed(indices):
                mask = self.masks.get(j, 0xFF)
                assert _is_simple_mask(mask)
                max_size = mask + 1

                if len(self.nodes[j]) < max_size and j not in self.forced:
                    # There are still byte values to explore at this node,
                    # so it isn't dead yet.
                    break
                if set(self.nodes[j].values()).issubset(self.dead):
                    # Everything beyond this node is known to be dead,
                    # and there are no more values to explore here (see above),
                    # so this node must be dead too.
                    self.dead.add(j)
                else:
                    # Even though all of this node's possible values have been
                    # tried, there are still some deeper nodes that remain
                    # alive, so this node isn't dead yet.
                    break

    def generate_novel_prefix(self, random):
        """Generate a short random string that (after rewriting) is not
        a prefix of any buffer previously added to the tree."""
        assert not self.is_exhausted
        prefix = bytearray()
        node = 0
        while True:
            assert len(prefix) < self.cap
            assert node not in self.dead

            # Figure out the range of byte values we should be trying.
            # Normally this will be 0-255, unless the current position has a
            # mask.
            mask = self.masks.get(node, 0xFF)
            assert _is_simple_mask(mask)
            upper_bound = mask + 1

            try:
                c = self.forced[node]
                # This position has a forced byte value, so trying a different
                # value wouldn't be helpful. Just add the forced byte, and
                # move on to the next position.
                prefix.append(c)
                node = self.nodes[node][c]
                continue
            except KeyError:
                pass

            # Provisionally choose the next byte value.
            # This will change later if we find that it was a bad choice.
            c = random.randrange(0, upper_bound)

            try:
                next_node = self.nodes[node][c]
                if next_node in self.dead:
                    # Whoops, the byte value we chose for this position has
                    # already been fully explored. Let's pick a new value, and
                    # this time choose a value that's definitely still alive.
                    choices = [
                        b
                        for b in hrange(upper_bound)
                        if self.nodes[node].get(b) not in self.dead
                    ]
                    assert choices
                    c = random.choice(choices)
                    node = self.nodes[node][c]
                else:
                    # The byte value we chose is in the tree, but it still has
                    # some unexplored descendants, so it's a valid choice.
                    node = next_node
                prefix.append(c)
            except KeyError:
                # The byte value we chose isn't in the tree at this position,
                # which means we've successfully found a novel prefix.
                prefix.append(c)
                break
        assert node not in self.dead
        return hbytes(prefix)

    def rewrite(self, buffer):
        """Use previously seen ConjectureData objects to return a tuple of
        the rewritten buffer and the status we would get from running that
        buffer with the test function. If the status cannot be predicted
        from the existing values it will be None."""
        buffer = hbytes(buffer)

        rewritten = bytearray()
        return_status = None

        node_index = 0
        for i, c in enumerate(buffer):
            # If there's a forced value or a mask at this position, then
            # pretend that the buffer already contains a matching value,
            # because the test function is going to do the same.
            try:
                c = self.forced[node_index]
            except KeyError:
                pass
            try:
                c = c & self.masks[node_index]
            except KeyError:
                pass

            try:
                # If we know how many bytes are read at this point and
                # there aren't enough, then it doesn't actually matter
                # what the values are, we're definitely going to overrun.
                if i + self.block_sizes[node_index] > len(buffer):
                    return_status = Status.OVERRUN
                    break
            except KeyError:
                pass

            rewritten.append(c)

            try:
                node_index = self.nodes[node_index][c]
            except KeyError:
                # The byte at this position isn't in the tree, which means
                # we haven't tested this buffer. Break out of the tree
                # traversal, and run the test function normally.
                rewritten.extend(buffer[i + 1 :])
                assert len(rewritten) == len(buffer)
                break
            node = self.nodes[node_index]
            if isinstance(node, Status):
                # This buffer (or a prefix of it) has already been tested.
                # Return the stored result instead of trying it again.
                assert node != Status.OVERRUN
                return_status = node
                break
        else:
            # Falling off the end of this loop means that we're about to test
            # a prefix of a previously-tested byte stream, so the test would
            # overrun.
            return_status = Status.OVERRUN

        return hbytes(rewritten), return_status


def _is_simple_mask(mask):
    """A simple mask is ``(2 ** n - 1)`` for some ``n``, so it has the effect
    of keeping the lowest ``n`` bits and discarding the rest.

    A mask in this form can produce any integer between 0 and the mask itself
    (inclusive), and the total number of these values is ``(mask + 1)``.
    """
    return (mask & (mask + 1)) == 0
