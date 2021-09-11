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

import pytest

from hypothesis import assume, given, strategies as st

from tests.array_api.common import xp, xps
from tests.common.debug import find_any

pytestmark = [pytest.mark.mockable_xp]


def test_indices_options():
    indexers = (
        xps.array_shapes(min_dims=1, max_dims=32)
        .flatmap(xps.indices)
        .map(lambda idx: idx if isinstance(idx, tuple) else (idx,))
    )
    find_any(indexers, lambda ix: Ellipsis in ix)
    find_any(indexers, lambda ix: Ellipsis not in ix)


def test_indices_can_generate_empty_tuple():
    find_any(xps.indices(shape=(0, 0), allow_ellipsis=True), lambda ix: ix == ())


def test_indices_can_generate_non_tuples():
    find_any(
        xps.indices(shape=(0, 0), allow_ellipsis=True),
        lambda ix: not isinstance(ix, tuple),
    )


def test_indices_can_generate_long_ellipsis():
    # Runs of slice(None) - such as [0,:,:,:,0] - can be replaced by e.g. [0,...,0]
    find_any(
        xps.indices(shape=(1, 0, 0, 0, 1), max_dims=3, allow_ellipsis=True),
        lambda ix: len(ix) == 3 and ix[1] == Ellipsis,
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


@given(st.data())
def test_indices_generate_valid_indexers(data):
    shape = data.draw(
        xps.array_shapes(min_dims=1, max_side=4)
        | xps.array_shapes(min_dims=1, min_side=1, max_side=10),
        label="shape",
    )
    min_dims = data.draw(st.integers(0, len(shape)), label="min_dims")
    max_dims = data.draw(
        st.none() | st.integers(min_dims, len(shape)), label="max_dims"
    )
    allow_ellipsis = data.draw(st.booleans(), "allow_ellipsis")
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
