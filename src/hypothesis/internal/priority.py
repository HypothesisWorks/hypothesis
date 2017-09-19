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

import attr


@attr.s(slots=True)
class Entry(object):
    key = attr.ib()
    value = attr.ib()


class PriorityMap(object):
    """This implements a priority map. That is, it is a mapping of keys to
    values like a normal dict, but it additionally supports an operation of
    giving you the key with the smallest value.

    It does so with no extra storage (theoretically - in actual practice this
    implementation doesn't implement the low level hash map operations itself
    and just uses Python's built in ones), and at an additonal O(log(n)) time
    cost when updating.

    The design idea is that we store an implicit binary heap inline in the
    entries for the hash table, and when swapping entries of the heap we update
    an index to them, so that we always know exactly where to look for the
    right entry based on its key.

    """

    __slots__ = ('__index', '__data')

    def __init__(self):
        # Entry objects for all of our mapping data, stored as an
        # implicit binary tree satisfying the heap property. That is, the
        # children of index i are 2 * i + 1 and 2 * i + 2, and whenever i is a
        # parent of j, self.__data[i].value <= self.__data[j].valule. In
        # particular this ensures that the self.__data[0] always has minimal
        # values among all entries.
        self.__data = []

        # Lookup table for getting the current index of a key. That is,
        # self.__data[self.__index[key]].key == key.

        # If we were implementing this in a lower level language this would
        # probably be much simpler than a full hash table and would just
        # contain indices placed at suitable points for the hash values of
        # their keys, but that isn't really worth doing in python and adds
        # needless complexity to understanding this approach.

        # https://morepypy.blogspot.co.uk/2015/01/faster-more-memory-efficient-and-more.html
        # for details of how it might look.
        self.__index = {}

    def __len__(self):
        # The length of a PriorityMap is just the number of entries. We keep
        # this in sync with the size of the index so as to not waste memory
        # keeping deleted keys around.
        assert len(self.__data) == len(self.__index)
        return len(self.__data)

    def __getitem__(self, key):
        # Getting the value associated with a key is a two part process: We
        # first look it up in the index to find out where in our entries it is,
        # then we get the value from the actual entry object.
        i = self.__index[key]
        entry = self.__data[i]
        assert key == entry.key
        return entry.value

    def __setitem__(self, key, value):
        # Setting an item consists of either finding the entry that already
        # corresponds to it, or creating a new one at the end of the array.
        try:
            i = self.__index[key]
        except KeyError:
            i = len(self.__data)
            self.__data.append(Entry(key, value))
        else:
            entry = self.__data[i]
            assert key == entry.key
            entry.value = value

        # We have now potentially changed the value at i (or created a new one)
        # so we may have violated the heap property there. Thus we must call
        # __fix to ensure that we
        self.__fix(i)

    def __delitem__(self, key):
        # deleting an item works as follows: We
        i = self.__index.pop(key)
        entry = self.__data[i]
        assert key == entry.key
        last = self.__data.pop()
        # i may now point past the end of the array if we were deleting the
        # last element of self.__data. If so the heap property is automatically
        # satisfied and there's nothing we need to do. If not, the entry at
        # index i is now a dead element, we replace it with the element we
        # just removed from the end of the array, and we then rebalance the
        # heap around that point.
        if i < len(self.__data):
            self.__data[i] = last
            self.__fix(i)

    def peek_min(self):
        """Returns a tuple (key, value) where value is minimal among all
        possible values in the map.

        If there are multiple keys with the minimal value, an arbitrary
        one is chosen.

        """
        min_entry = self.__data[0]
        return (min_entry.key, min_entry.value)

    def assert_valid(self):
        """Method for checking that the map satisfies all our desired
        invariants.

        If everything is working correctly this should be an O(n) no-op.
        There should be no reason to call this method outside of tests
        if our testing is up to scratch.

        """

        assert len(self.__data) == len(self.__index)
        for i, entry in enumerate(self.__data):
            assert self.__index[entry.key] == i

            # Check that the heap property is satisfied for every parent/child
            # pair.
            for j in (2 * i + 1, 2 * i + 2):
                if j < len(self.__data):
                    assert entry.value <= self.__data[j].value

    def __fix(self, i):
        """Called when the heap property is satisfied for every pair of indices
        except onces involving i. i.e. we have modified the heap in a way that
        fails to satisfy the invariant around i and we now wish to fix this.

        This performs at most ceil(log2(len(self))) (the height of the
        implict tree) swaps.

        """

        self.__index[self.__data[i].key] = i

        while i > 0:
            parent = (i - 1) // 2
            if self.__swap_out_of_order(parent, i):
                i = parent
            else:
                break

        while True:
            child1 = i * 2 + 1
            child2 = i * 2 + 2
            if child1 >= len(self.__data):
                break
            if child2 < len(self.__data):
                # If there are two children we pick the smaller of the two.
                # This ensures that when we move the child up to the current
                # index the heap property is satisfied between it and the other
                # child.
                child = min(
                    (child1, child2), key=lambda j: self.__data[j].value)
            else:
                child = child1
            if self.__swap_out_of_order(i, child):
                i = child
            else:
                break

    def __swap_out_of_order(self, i, j):
        """Check if the values of i and j are in the correct order.

        If not, return True and swap them so that they are in order,
        maintaining the invariant that the index points to the right
        place.

        """

        # This should only be called when i is the parent of j.
        assert j > 0
        assert (j - 1) // 2 == i

        if self.__data[i].value > self.__data[j].value:
            self.__data[i], self.__data[j] = self.__data[j], self.__data[i]
            for k in (i, j):
                self.__index[self.__data[k].key] = k
            return True
        else:
            return False
