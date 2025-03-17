# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import strategies as st

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
