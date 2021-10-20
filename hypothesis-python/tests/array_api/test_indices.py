# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
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

import math

from hypothesis import assume, given, strategies as st

from tests.array_api.common import xp, xps
from tests.common.debug import find_any


def test_generate_indices_with_and_without_ellipsis():
    """Strategy can generate indices with and without Ellipsis."""
    strat = (
        xps.array_shapes(min_dims=1, max_dims=32)
        .flatmap(xps.indices)
        .map(lambda idx: idx if isinstance(idx, tuple) else (idx,))
    )
    find_any(strat, lambda ix: Ellipsis in ix)
    find_any(strat, lambda ix: Ellipsis not in ix)


def test_generate_empty_tuple():
    """Strategy generates empty tuples as indices."""
    find_any(xps.indices(shape=(0, 0), allow_ellipsis=True), lambda ix: ix == ())


def test_generate_non_tuples():
    """Strategy generates non-tuples as indices."""
    find_any(
        xps.indices(shape=(0, 0), allow_ellipsis=True),
        lambda ix: not isinstance(ix, tuple),
    )


def test_generate_long_ellipsis():
    """Strategy can replace runs of slice(None) with Ellipsis.

    We specifically test if [0,...,0] is generated alongside [0,:,:,:,0]
    """
    strat = xps.indices(shape=(1, 0, 0, 0, 1), max_dims=3, allow_ellipsis=True)
    find_any(strat, lambda ix: len(ix) == 3 and ix[1] == Ellipsis)
    find_any(
        strat,
        lambda ix: len(ix) == 5
        and all(isinstance(key, slice) and key == slice(None) for key in ix[1:3]),
    )


@given(
    xps.indices(shape=(0, 0, 0, 0, 0), max_dims=5).filter(
        lambda idx: isinstance(idx, tuple) and Ellipsis in idx
    )
)
def test_indices_replaces_whole_axis_slices_with_ellipsis(idx):
    # `slice(None)` (aka `:`) is the only valid index for an axis of size
    # zero, so if all dimensions are 0 then a `...` will replace all the
    # slices because we generate `...` for entire contiguous runs of `:`
    assert slice(None) not in idx


@given(xps.indices((3, 3, 3, 3, 3)))
def test_indices_effeciently_generate_indexers(_):
    """Generation is not too slow."""


@given(
    shape=xps.array_shapes(min_dims=1, max_side=4)
    | xps.array_shapes(min_dims=1, min_side=0, max_side=10),
    allow_ellipsis=st.booleans(),
    data=st.data(),
)
def test_indices_generate_valid_indexers(shape, allow_ellipsis, data):
    """Strategy generates valid indices."""
    min_dims = data.draw(st.integers(0, len(shape)), label="min_dims")
    max_dims = data.draw(
        st.none() | st.integers(min_dims, len(shape)), label="max_dims"
    )
    indexer = data.draw(
        xps.indices(
            shape,
            min_dims=min_dims,
            max_dims=max_dims,
            allow_ellipsis=allow_ellipsis,
        ),
        label="indexer",
    )

    # Check that disallowed things are indeed absent
    if isinstance(indexer, tuple):
        assert 0 <= len(indexer) <= len(shape) + int(allow_ellipsis)
    else:
        assert 1 <= len(shape) + int(allow_ellipsis)
    assert None not in shape
    if not allow_ellipsis:
        assert Ellipsis not in shape

    if 0 in shape:
        # If there's a zero in the shape, the array will have no elements.
        array = xp.zeros(shape)
        assert array.size == 0
    elif math.prod(shape) <= 10 ** 5:
        # If it's small enough to instantiate, do so with distinct elements.
        array = xp.reshape(xp.arange(math.prod(shape)), shape)
    else:
        # We can't cheat on this one, so just try another.
        assume(False)

    # Finally, check that we can use our indexer without error
    array[indexer]
