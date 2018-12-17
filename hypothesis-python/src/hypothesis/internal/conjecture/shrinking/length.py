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

from __future__ import absolute_import, division, print_function

from hypothesis.internal.conjecture.shrinking.common import Shrinker, find_integer


"""
This module implements a length minimizer for sequences.

That is, given some sequence of elements satisfying some predicate, it tries to
find a strictly shorter one satisfying the same predicate.

Doing so perfectly is provably exponential. This only implements a linear time
worst case algorithm which guarantees certain minimality properties of the
fixed point.
"""


class Length(Shrinker):
    """Attempts to find a smaller sequence satisfying f. Will only perform
    linearly many evaluations, and does not loop to a fixed point.

    Guarantees made at a fixed point:

        1. No individual element may be deleted.
        2. No *adjacent* pair of elements may be deleted.
    """

    def make_immutable(self, value):
        return tuple(value)

    def short_circuit(self):
        return self.consider(()) or len(self.current) <= 1

    def left_is_better(self, left, right):
        return len(left) < len(right)

    def run_step(self):
        # Try to delete as many elements as possible from the sequence, in
        # (roughly) one pass, from right to left.

        # Starting from the end of the sequence, we try to delete as many
        # consecutive elements as possible. When we encounter an element that
        # can't be deleted this way, we skip over it for the rest of the pass,
        # and continue to its left. This lets us finish a pass in linear time,
        # but the drawback is that we'll miss some possible deletions of
        # already-skipped elements.
        skipped = 0

        # When every element has been deleted or skipped, the pass is complete.
        while skipped < len(self.current):
            # Number of remaining elements to the left of the skipped region.
            # These are all candidates for attempted deletion.
            candidates = len(self.current) - skipped

            # Take a stable snapshot of the current sequence, so that deleting
            # elements doesn't mess with our slice indices.
            start = self.current

            # Delete as many elements as possible (k) from the candidate
            # region, from right to left. Always retain the skipped elements
            # at the end. (See diagram below.)
            find_integer(
                lambda k: k <= candidates
                and self.consider(start[: candidates - k] + start[candidates:])
            )

            # If we stopped because of an element we couldn't delete, enlarge
            # the skipped region to include it, and continue. (If we stopped
            # because we deleted everything, the loop is about to end anyway.)
            skipped += 1


# This diagram shows how we use two slices to delete (k) elements from the
# candidate region, while retaining the other candidates, and retaining all of
# the skipped elements.
#                              <==================
#          candidates                skipped
#  /^^^^^^^^^^^^^^^^^^^^^^^^^\ /^^^^^^^^^^^^^^^^^\
# +---+---+---+---+---+---+---+---+---+---+---+---+
# |   |   |   |   |   |   |   |   |   |   |   |   |
# +---+---+---+---+---+---+---+---+---+---+---+---+
#  \_________________/ \#####/ \_________________/
#    [:candidates-k]      k       [candidates:]
#                      <======
