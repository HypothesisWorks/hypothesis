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

import hypothesis.internal.conjecture.utils as d
from hypothesis.internal.compat import bit_length, hrange
from hypothesis.searchstrategy.strategies import SearchStrategy, filter_not_satisfied


class BoolStrategy(SearchStrategy):
    """A strategy that produces Booleans with a Bernoulli conditional
    distribution."""

    def __repr__(self):
        return u"BoolStrategy()"

    def calc_has_reusable_values(self, recur):
        return True

    def do_draw(self, data):
        return d.boolean(data)


def is_simple_data(value):
    try:
        hash(value)
        return True
    except TypeError:
        return False


class JustStrategy(SearchStrategy):
    """A strategy which always returns a single fixed value."""

    def __init__(self, value):
        SearchStrategy.__init__(self)
        self.value = value

    def __repr__(self):
        return "just(%r)" % (self.value,)

    def calc_has_reusable_values(self, recur):
        return True

    def calc_is_cacheable(self, recur):
        return is_simple_data(self.value)

    def do_draw(self, data):
        return self.value


class SampledFromStrategy(SearchStrategy):
    """A strategy which samples from a set of elements. This is essentially
    equivalent to using a OneOfStrategy over Just strategies but may be more
    efficient and convenient.

    The conditional distribution chooses uniformly at random from some
    non-empty subset of the elements.
    """

    def __init__(self, elements):
        SearchStrategy.__init__(self)
        self.elements = d.check_sample(elements, "sampled_from")
        assert self.elements

    def calc_has_reusable_values(self, recur):
        return True

    def calc_is_cacheable(self, recur):
        return is_simple_data(self.elements)

    def do_draw(self, data):
        return d.choice(data, self.elements)

    def do_filtered_draw(self, data, filter_strategy):
        # Set of indices that have been tried so far, so that we never test
        # the same element twice during a draw.
        known_bad_indices = set()

        def check_index(i):
            """Return ``True`` if the element at ``i`` satisfies the filter
            condition.
            """
            if i in known_bad_indices:
                return False
            ok = filter_strategy.condition(self.elements[i])
            if not ok:
                if not known_bad_indices:
                    filter_strategy.note_retried(data)
                known_bad_indices.add(i)
            return ok

        # Start with ordinary rejection sampling. It's fast if it works, and
        # if it doesn't work then it was only a small amount of overhead.
        for _ in hrange(3):
            i = d.integer_range(data, 0, len(self.elements) - 1)
            if check_index(i):
                return self.elements[i]

        # If we've tried all the possible elements, give up now.
        max_good_indices = len(self.elements) - len(known_bad_indices)
        if not max_good_indices:
            return filter_not_satisfied

        # Figure out the bit-length of the index that we will write back after
        # choosing an allowed element.
        write_length = bit_length(len(self.elements))

        # Impose an arbitrary cutoff to prevent us from wasting too much time
        # on very large element lists.
        cutoff = 10000
        max_good_indices = min(max_good_indices, cutoff)

        # Before building the list of allowed indices, speculatively choose
        # one of them. We don't yet know how many allowed indices there will be,
        # so this choice might be out-of-bounds, but that's OK.
        speculative_index = d.integer_range(data, 0, max_good_indices - 1)

        # Calculate the indices of allowed values, so that we can choose one
        # of them at random. But if we encounter the speculatively-chosen one,
        # just use that and return immediately.
        allowed_indices = []
        for i in hrange(min(len(self.elements), cutoff)):
            if check_index(i):
                allowed_indices.append(i)
                if len(allowed_indices) > speculative_index:
                    # Early-exit case: We reached the speculative index, so
                    # we just return the corresponding element.
                    data.draw_bits(write_length, forced=i)
                    return self.elements[i]

        # The speculative index didn't work out, but at this point we've built
        # the complete list of allowed indices, so we can just choose one of
        # them.
        if allowed_indices:
            i = d.choice(data, allowed_indices)
            data.draw_bits(write_length, forced=i)
            return self.elements[i]
        # If there are no allowed indices, the filter couldn't be satisfied.

        return filter_not_satisfied
