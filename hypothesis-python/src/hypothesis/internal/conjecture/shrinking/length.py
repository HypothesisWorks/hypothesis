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

from hypothesis.internal.compat import hrange
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
        # Try to delete as many elements as possible from the sequence, trying
        # each element no more than once.

        # We convert the sequence to a set of indices. This allows us to more
        # easily do book-keeping around which elements we've tried removing.
        initial = self.current

        indices = list(hrange(len(self.current)))

        # The set of indices that we have not yet removed (either because
        # we have not yet tried to remove them or because we tried and
        # failed).
        current_subset = set(indices)

        # The set of indices in current_subset that we have not yet tried
        # to remove.
        candidates_for_removal = set(current_subset)

        def consider_set(keep):
            """Try replacing current_subset with current_subset & keep."""

            keep = keep & current_subset
            to_remove = current_subset - keep

            # Once we've tried and failed to delete an element we never
            # attempt to delete it again in the current pass. This can cause
            # us to skip shrinks that would work, but that doesn't matter -
            # if this pass succeeded then it will run again at some point,
            # so those will be picked up later.
            if not to_remove.issubset(candidates_for_removal):
                return False
            if self.consider([v for i, v in enumerate(initial) if i in keep]):
                current_subset.intersection_update(keep)
                return True
            return False

        # We iterate over the indices in random order. This is because deletions
        # towards the end are more likely to work, while deletions from the
        # beginning are more likely to have higher impact. In addition there
        # tend to be large "dead" regions where nothing can be deleted, and
        # by proceeding in random order we don't have long gaps in those where
        # we make no progress.
        #
        # Note that this may be strictly more expensive than iterating from
        # left to right or right to left. The cost of find_integer, say f, is
        # convex. When deleting n elements starting from the left we pay f(n)
        # invocations, but when starting from the middle we pay 2 f(n / 2)
        # > f(n) invocations. In this case we are prioritising making progress
        # over a possibly strictly lower cost for two reasons: Firstly, when
        # n is small we just do linear scans anyway so this doesn't actually
        # matter, and secondly because successfuly deletions will tend to
        # speed up the test function and thus even when we make more test
        # function calls we may still win on time.
        #
        # It's also very frustrating watching the shrinker repeatedly fail
        # to delete, so there's a psychological benefit to prioritising
        # progress over cost.
        self.random.shuffle(indices)
        for i in indices:
            candidates_for_removal &= current_subset
            if not candidates_for_removal:
                break

            # We have already processed this index, either because it was bulk
            # removed or is the end point of a set that was.
            if i not in candidates_for_removal:
                continue

            # Note that we do not update candidates_for_removal until we've
            # actually tried removing them. This is because our consider_set
            # predicate checks whether we've previously tried deleting them,
            # so removing them here would result in wrong checks!

            # We now try to delete a region around i. We start by trying to
            # delete a region starting with i, i.e. [i, j) for some j > i.
            to_right = find_integer(
                lambda n: i + n <= len(initial)
                and consider_set(current_subset - set(hrange(i, i + n)))
            )

            # If that succeeded we're in a deletable region. It's unlikely that
            # we happened to pick the starting index of that region, so we try
            # to extend it to the left too.
            if to_right > 0:
                to_left = find_integer(
                    lambda n: i - n >= 0
                    and consider_set(current_subset - set(hrange(i - n, i)))
                )

                # find_integer always tries at least n + 1 when it returns n.
                # This means that we've tried deleting i - (to_left + 1) and
                # failed to do so, so we can remove it from our candidates for
                # deletion.
                candidates_for_removal.discard(i - to_left - 1)

            # We've now tried deleting i so remove it.
            candidates_for_removal.discard(i)

            # As per comment above we've also tried deleting one past the end
            # of the region so we remove that from the candidate set too.
            candidates_for_removal.discard(i + to_right)
