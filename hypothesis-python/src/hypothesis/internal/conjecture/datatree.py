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

from hypothesis.internal.compat import hbytes
from hypothesis.internal.conjecture.data import DataObserver


class DataTree(object):
    """Tracks the tree structure of a collection of ConjectureData
    objects, for use in ConjectureRunner."""

    def __init__(self):
        pass

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
        return DataObserver()


def _is_simple_mask(mask):
    """A simple mask is ``(2 ** n - 1)`` for some ``n``, so it has the effect
    of keeping the lowest ``n`` bits and discarding the rest.

    A mask in this form can produce any integer between 0 and the mask itself
    (inclusive), and the total number of these values is ``(mask + 1)``.
    """
    return (mask & (mask + 1)) == 0


class TreeRecordingObserver(DataObserver):
    def __init__(self, tree):
        self.__tree = tree

    def init(self, data):
        self.__data = data

    def conclude_test(self, status, interesting_origin):
        self.__tree.add(self.__data)
