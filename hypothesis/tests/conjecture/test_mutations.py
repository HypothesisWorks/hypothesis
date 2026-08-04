# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import given, seed, settings, strategies as st

from tests.common.debug import find_any

tree = st.deferred(lambda: st.tuples(st.integers(), tree, tree)) | st.just(None)


def test_can_find_duplicated_subtree():
    # look for an example of the form
    #
    #                  ┌─────┐
    #           ┌──────┤  a  ├──────┐
    #           │      └─────┘      │
    #        ┌──┴──┐             ┌──┴──┐
    #        │  b  │             │  a  │
    #        └──┬──┘             └──┬──┘
    #      ┌────┴────┐         ┌────┴────┐
    #   ┌──┴──┐   ┌──┴──┐   ┌──┴──┐   ┌──┴──┐
    #   │  c  │   │  d  │   │  b  │   │ ... │
    #   └─────┘   └─────┘   └──┬──┘   └─────┘
    #                     ┌────┴────┐
    #                  ┌──┴──┐   ┌──┴──┐
    #                  │  c  │   │  d  │
    #                  └─────┘   └─────┘
    #
    # If we just checked that (b, c, d) was duplicated somewhere, this could have
    # happened as a result of normal mutation. Checking for the a parent node as
    # well is unlikely to have been generated without tree mutation, however.
    find_any(
        tree,
        (
            lambda v: v is not None
            and v[1] is not None
            and v[2] is not None
            and v[0] == v[2][0]
            and v[1] == v[2][1]
        ),
    )


def test_mutations_avoid_duplicating_within_unique_collections():
    # Duplicating one element of a unique collection onto another element of
    # the same collection is certain to be rejected, wasting (potentially
    # expensive) element draws.
    executions = 0
    delivered = 0

    @st.composite
    def counted_integers(draw):
        nonlocal executions
        executions += 1
        return draw(st.integers())

    @seed(0)
    @settings(max_examples=100, database=None)
    @given(st.sets(counted_integers(), min_size=3, max_size=3))
    def t(x):
        nonlocal delivered
        delivered += len(x)

    t()
    # around 6x before we taught the mutator about uniqueness; now ~1.06x
    assert executions <= 1.5 * delivered


def test_can_duplicate_between_unique_collections():
    # While the mutator avoids duplicating elements within a single unique
    # collection, duplicating between two different collections is still
    # possible (and useful).
    unique_lists = st.lists(st.integers(), unique=True, min_size=1, max_size=5)
    find_any(
        st.tuples(unique_lists, unique_lists),
        lambda t: bool({x for x in t[0] if abs(x) > 2**40} & set(t[1])),
    )
