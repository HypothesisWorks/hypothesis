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

import pytest

from hypothesis.errors import InvalidArgument

from tests.array_api.common import xp, xps

pytestmark = [pytest.mark.mockable_xp]


def e(a, **kwargs):
    kw = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
    return pytest.param(a, kwargs, id=f"{a.__name__}({kw})")


@pytest.mark.parametrize(
    ("function", "kwargs"),
    [
        e(xps.arrays, dtype=xp.int8, shape=(0.5,)),
        e(xps.arrays, dtype=xp.int8, shape=1, fill=3),
        e(xps.arrays, dtype=xp.int8, shape=1, elements="not a strategy"),
        e(xps.array_shapes, min_side=2, max_side=1),
        e(xps.array_shapes, min_dims=3, max_dims=2),
        e(xps.array_shapes, min_dims=-1),
        e(xps.array_shapes, min_side=-1),
        e(xps.array_shapes, min_side="not an int"),
        e(xps.array_shapes, max_side="not an int"),
        e(xps.array_shapes, min_dims="not an int"),
        e(xps.array_shapes, max_dims="not an int"),
        e(xps.from_dtype, dtype=1),
        e(xps.from_dtype, dtype=xp.int8, min_value="not an int"),
        e(xps.from_dtype, dtype=xp.int8, max_value="not an int"),
        e(xps.from_dtype, dtype=xp.float32, min_value="not a float"),
        e(xps.from_dtype, dtype=xp.float32, max_value="not a float"),
        e(xps.from_dtype, dtype=xp.int8, min_value=10, max_value=5),
        e(xps.from_dtype, dtype=xp.float32, min_value=10, max_value=5),
        e(xps.from_dtype, dtype=xp.int8, min_value=-999),
        e(xps.from_dtype, dtype=xp.int8, max_value=-999),
        e(xps.from_dtype, dtype=xp.int8, min_value=999),
        e(xps.from_dtype, dtype=xp.int8, max_value=999),
        e(xps.from_dtype, dtype=xp.uint8, min_value=-999),
        e(xps.from_dtype, dtype=xp.uint8, max_value=-999),
        e(xps.from_dtype, dtype=xp.uint8, min_value=999),
        e(xps.from_dtype, dtype=xp.uint8, max_value=999),
        e(xps.from_dtype, dtype=xp.float32, min_value=-4e38),
        e(xps.from_dtype, dtype=xp.float32, max_value=-4e38),
        e(xps.from_dtype, dtype=xp.float32, min_value=4e38),
        e(xps.from_dtype, dtype=xp.float32, max_value=4e38),
        e(xps.integer_dtypes, sizes=()),
        e(xps.integer_dtypes, sizes=(3,)),
        e(xps.unsigned_integer_dtypes, sizes=()),
        e(xps.unsigned_integer_dtypes, sizes=(3,)),
        e(xps.floating_dtypes, sizes=()),
        e(xps.floating_dtypes, sizes=(3,)),
        e(xps.valid_tuple_axes, ndim=-1),
        e(xps.valid_tuple_axes, ndim=2, min_size=-1),
        e(xps.valid_tuple_axes, ndim=2, min_size=3, max_size=10),
        e(xps.valid_tuple_axes, ndim=2, min_size=2, max_size=1),
        e(xps.valid_tuple_axes, ndim=2.0, min_size=2, max_size=1),
        e(xps.valid_tuple_axes, ndim=2, min_size=1.0, max_size=2),
        e(xps.valid_tuple_axes, ndim=2, min_size=1, max_size=2.0),
        e(xps.valid_tuple_axes, ndim=2, min_size=1, max_size=3),
        e(xps.broadcastable_shapes, shape="a"),
        e(xps.broadcastable_shapes, shape=(2, 2), min_side="a"),
        e(xps.broadcastable_shapes, shape=(2, 2), min_dims="a"),
        e(xps.broadcastable_shapes, shape=(2, 2), max_side="a"),
        e(xps.broadcastable_shapes, shape=(2, 2), max_dims="a"),
        e(xps.broadcastable_shapes, shape=(2, 2), min_side=-1),
        e(xps.broadcastable_shapes, shape=(2, 2), min_dims=-1),
        e(xps.broadcastable_shapes, shape=(2, 2), min_side=1, max_side=0),
        e(xps.broadcastable_shapes, shape=(2, 2), min_dims=1, max_dims=0),
        e(
            xps.broadcastable_shapes,  # max_side too small
            shape=(5, 1),
            min_dims=2,
            max_dims=4,
            min_side=2,
            max_side=3,
        ),
        e(
            xps.broadcastable_shapes,  # min_side too large
            shape=(0, 1),
            min_dims=2,
            max_dims=4,
            min_side=2,
            max_side=3,
        ),
        e(
            xps.broadcastable_shapes,  # default max_dims unsatisfiable
            shape=(5, 3, 2, 1),
            min_dims=3,
            max_dims=None,
            min_side=2,
            max_side=3,
        ),
        e(
            xps.broadcastable_shapes,  # default max_dims unsatisfiable
            shape=(0, 3, 2, 1),
            min_dims=3,
            max_dims=None,
            min_side=2,
            max_side=3,
        ),
        e(xps.mutually_broadcastable_shapes, num_shapes=0),
        e(xps.mutually_broadcastable_shapes, num_shapes="a"),
        e(xps.mutually_broadcastable_shapes, num_shapes=2, base_shape="a"),
        e(
            xps.mutually_broadcastable_shapes,  # min_side is invalid type
            num_shapes=2,
            min_side="a",
        ),
        e(
            xps.mutually_broadcastable_shapes,  # min_dims is invalid type
            num_shapes=2,
            min_dims="a",
        ),
        e(
            xps.mutually_broadcastable_shapes,  # max_side is invalid type
            num_shapes=2,
            max_side="a",
        ),
        e(
            xps.mutually_broadcastable_shapes,  # max_side is invalid type
            num_shapes=2,
            max_dims="a",
        ),
        e(
            xps.mutually_broadcastable_shapes,  # min_side is out of domain
            num_shapes=2,
            min_side=-1,
        ),
        e(
            xps.mutually_broadcastable_shapes,  # min_dims is out of domain
            num_shapes=2,
            min_dims=-1,
        ),
        e(
            xps.mutually_broadcastable_shapes,  # max_side < min_side
            num_shapes=2,
            min_side=1,
            max_side=0,
        ),
        e(
            xps.mutually_broadcastable_shapes,  # max_dims < min_dims
            num_shapes=2,
            min_dims=1,
            max_dims=0,
        ),
        e(
            xps.mutually_broadcastable_shapes,  # max_side too small
            num_shapes=2,
            base_shape=(5, 1),
            min_dims=2,
            max_dims=4,
            min_side=2,
            max_side=3,
        ),
        e(
            xps.mutually_broadcastable_shapes,  # min_side too large
            num_shapes=2,
            base_shape=(0, 1),
            min_dims=2,
            max_dims=4,
            min_side=2,
            max_side=3,
        ),
        e(
            xps.mutually_broadcastable_shapes,  # user-specified max_dims unsatisfiable
            num_shapes=1,
            base_shape=(5, 3, 2, 1),
            min_dims=3,
            max_dims=4,
            min_side=2,
            max_side=3,
        ),
        e(
            xps.mutually_broadcastable_shapes,  # user-specified max_dims unsatisfiable
            num_shapes=2,
            base_shape=(0, 3, 2, 1),
            min_dims=3,
            max_dims=4,
            min_side=2,
            max_side=3,
        ),
        e(xps.indices, shape=0),
        e(xps.indices, shape=("1", "2")),
        e(xps.indices, shape=(0, -1)),
        e(xps.indices, shape=(0, 0), allow_newaxis=None),
        e(xps.indices, shape=(0, 0), allow_ellipsis=None),
        e(xps.indices, shape=(0, 0), min_dims=-1),
        e(xps.indices, shape=(0, 0), min_dims=1.0),
        e(xps.indices, shape=(0, 0), max_dims=-1),
        e(xps.indices, shape=(0, 0), max_dims=1.0),
        e(xps.indices, shape=(0, 0), min_dims=2, max_dims=1),
        e(xps.indices, shape=()),
        e(xps.indices, shape=5, min_dims=0),
    ],
)
def test_raise_invalid_argument(function, kwargs):
    """Strategies raise helpful error with invalid arguments."""
    with pytest.raises(InvalidArgument):
        function(**kwargs).example()
