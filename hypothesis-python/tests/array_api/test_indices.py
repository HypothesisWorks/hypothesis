# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import math

import pytest

from hypothesis import assume, given, note, strategies as st
from hypothesis.extra._array_helpers import NDIM_MAX

from tests.common.debug import assert_all_examples, find_any


@pytest.mark.parametrize(
    "condition",
    [
        lambda ix: Ellipsis in ix,
        lambda ix: Ellipsis not in ix,
        lambda ix: None in ix,
        lambda ix: None not in ix,
    ],
)
def test_generate_optional_indices(xp, xps, condition):
    """Strategy can generate indices with optional values."""
    strat = (
        xps.array_shapes(min_dims=1, max_dims=32)
        .flatmap(lambda s: xps.indices(s, allow_newaxis=True))
        .map(lambda idx: idx if isinstance(idx, tuple) else (idx,))
    )
    find_any(strat, condition)


def test_cannot_generate_newaxis_when_disabled(xp, xps):
    """Strategy does not generate newaxis when disabled (i.e. the default)."""
    assert_all_examples(
        xps.indices((3, 3, 3)), lambda idx: idx == ... or None not in idx
    )


def test_generate_indices_for_0d_shape(xp, xps):
    """Strategy only generates empty tuples or Ellipsis as indices for an empty
    shape."""
    assert_all_examples(
        xps.indices(shape=(), allow_ellipsis=True),
        lambda idx: idx in [(), Ellipsis, (Ellipsis,)],
    )


def test_generate_tuples_and_non_tuples_for_1d_shape(xp, xps):
    """Strategy can generate tuple and non-tuple indices with a 1-dimensional shape."""
    strat = xps.indices(shape=(1,), allow_ellipsis=True)
    find_any(strat, lambda ix: isinstance(ix, tuple))
    find_any(strat, lambda ix: not isinstance(ix, tuple))


def test_generate_long_ellipsis(xp, xps):
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


def test_indices_replaces_whole_axis_slices_with_ellipsis(xp, xps):
    # `slice(None)` (aka `:`) is the only valid index for an axis of size
    # zero, so if all dimensions are 0 then a `...` will replace all the
    # slices because we generate `...` for entire contiguous runs of `:`
    assert_all_examples(
        xps.indices(shape=(0, 0, 0, 0, 0), max_dims=5).filter(
            lambda idx: isinstance(idx, tuple) and Ellipsis in idx
        ),
        lambda idx: slice(None) not in idx,
    )


def test_efficiently_generate_indexers(xp, xps):
    """Generation is not too slow."""
    find_any(xps.indices((3, 3, 3, 3, 3)))


@given(allow_newaxis=st.booleans(), allow_ellipsis=st.booleans(), data=st.data())
def test_generate_valid_indices(xp, xps, allow_newaxis, allow_ellipsis, data):
    """Strategy generates valid indices."""
    shape = data.draw(
        xps.array_shapes(min_dims=1, max_side=4)
        | xps.array_shapes(min_dims=1, min_side=0, max_side=10),
        label="shape",
    )
    min_dims = data.draw(
        st.integers(0, len(shape) if not allow_newaxis else len(shape) + 2),
        label="min_dims",
    )
    max_dims = data.draw(
        st.none()
        | st.integers(min_dims, len(shape) if not allow_newaxis else NDIM_MAX),
        label="max_dims",
    )
    indexer = data.draw(
        xps.indices(
            shape,
            min_dims=min_dims,
            max_dims=max_dims,
            allow_newaxis=allow_newaxis,
            allow_ellipsis=allow_ellipsis,
        ),
        label="indexer",
    )

    _indexer = indexer if isinstance(indexer, tuple) else (indexer,)
    # Check that disallowed things are indeed absent
    if not allow_ellipsis:
        assert Ellipsis not in _indexer
    if not allow_newaxis:
        assert None not in _indexer  # i.e. xp.newaxis
    # Check index is composed of valid objects
    for i in _indexer:
        assert isinstance(i, (int, slice)) or i is None or i == Ellipsis
    # Check indexer does not flat index
    nonexpanding_indexer = [i for i in _indexer if i is not None]
    if Ellipsis in _indexer:
        assert sum(i == Ellipsis for i in _indexer) == 1
        # Note ellipsis can index 0 axes
        assert len(nonexpanding_indexer) <= len(shape) + 1
    else:
        assert len(nonexpanding_indexer) == len(shape)

    if 0 in shape:
        # If there's a zero in the shape, the array will have no elements.
        array = xp.zeros(shape)
        assert array.size == 0  # sanity check
    elif math.prod(shape) <= 10**5:
        # If it's small enough to instantiate, do so with distinct elements.
        array = xp.reshape(xp.arange(math.prod(shape)), shape)
    else:
        # We can't cheat on this one, so just try another.
        assume(False)
    # Finally, check that we can use our indexer without error
    note(f"{array=}")
    array[indexer]
