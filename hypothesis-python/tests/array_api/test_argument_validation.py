# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from typing import Optional

import pytest

from hypothesis.errors import InvalidArgument
from hypothesis.extra.array_api import NominalVersion, make_strategies_namespace

from tests.array_api.common import MIN_VER_FOR_COMPLEX
from tests.common.debug import check_can_generate_examples


def e(name, *, _min_version: Optional[NominalVersion] = None, **kwargs):
    kw = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
    id_ = f"{name}({kw})"
    if _min_version is None:
        marks = ()
    else:
        marks = pytest.mark.xp_min_version(_min_version)
    return pytest.param(name, kwargs, id=id_, marks=marks)


@pytest.mark.parametrize(
    ("strat_name", "kwargs"),
    [
        e("arrays", dtype=1, shape=5),
        e("arrays", dtype=None, shape=5),
        e("arrays", dtype="int8", shape=(0.5,)),
        e("arrays", dtype="int8", shape=1, fill=3),
        e("arrays", dtype="int8", shape=1, elements="not a strategy"),
        e("arrays", dtype="int8", shape="not a shape or strategy"),
        e("array_shapes", min_side=2, max_side=1),
        e("array_shapes", min_dims=3, max_dims=2),
        e("array_shapes", min_dims=-1),
        e("array_shapes", min_side=-1),
        e("array_shapes", min_side="not an int"),
        e("array_shapes", max_side="not an int"),
        e("array_shapes", min_dims="not an int"),
        e("array_shapes", max_dims="not an int"),
        e("from_dtype", dtype=1),
        e("from_dtype", dtype=None),
        e("from_dtype", dtype="int8", min_value="not an int"),
        e("from_dtype", dtype="int8", max_value="not an int"),
        e("from_dtype", dtype="float32", min_value="not a float"),
        e("from_dtype", dtype="float32", max_value="not a float"),
        e("from_dtype", dtype="int8", min_value=10, max_value=5),
        e("from_dtype", dtype="float32", min_value=10, max_value=5),
        e("from_dtype", dtype="int8", min_value=-999),
        e("from_dtype", dtype="int8", max_value=-999),
        e("from_dtype", dtype="int8", min_value=999),
        e("from_dtype", dtype="int8", max_value=999),
        e("from_dtype", dtype="uint8", min_value=-999),
        e("from_dtype", dtype="uint8", max_value=-999),
        e("from_dtype", dtype="uint8", min_value=999),
        e("from_dtype", dtype="uint8", max_value=999),
        e("from_dtype", dtype="float32", min_value=-4e38),
        e("from_dtype", dtype="float32", max_value=-4e38),
        e("from_dtype", dtype="float32", min_value=4e38),
        e("from_dtype", dtype="float32", max_value=4e38),
        e("integer_dtypes", sizes=()),
        e("integer_dtypes", sizes=(3,)),
        e("unsigned_integer_dtypes", sizes=()),
        e("unsigned_integer_dtypes", sizes=(3,)),
        e("floating_dtypes", sizes=()),
        e("floating_dtypes", sizes=(3,)),
        e("complex_dtypes", _min_version=MIN_VER_FOR_COMPLEX, sizes=()),
        e("complex_dtypes", _min_version=MIN_VER_FOR_COMPLEX, sizes=(3,)),
        e("valid_tuple_axes", ndim=-1),
        e("valid_tuple_axes", ndim=2, min_size=-1),
        e("valid_tuple_axes", ndim=2, min_size=3, max_size=10),
        e("valid_tuple_axes", ndim=2, min_size=2, max_size=1),
        e("valid_tuple_axes", ndim=2.0, min_size=2, max_size=1),
        e("valid_tuple_axes", ndim=2, min_size=1.0, max_size=2),
        e("valid_tuple_axes", ndim=2, min_size=1, max_size=2.0),
        e("valid_tuple_axes", ndim=2, min_size=1, max_size=3),
        e("broadcastable_shapes", shape="a"),
        e("broadcastable_shapes", shape=(2, 2), min_side="a"),
        e("broadcastable_shapes", shape=(2, 2), min_dims="a"),
        e("broadcastable_shapes", shape=(2, 2), max_side="a"),
        e("broadcastable_shapes", shape=(2, 2), max_dims="a"),
        e("broadcastable_shapes", shape=(2, 2), min_side=-1),
        e("broadcastable_shapes", shape=(2, 2), min_dims=-1),
        e("broadcastable_shapes", shape=(2, 2), min_side=1, max_side=0),
        e("broadcastable_shapes", shape=(2, 2), min_dims=1, max_dims=0),
        e(
            "broadcastable_shapes",  # max_side too small
            shape=(5, 1),
            min_dims=2,
            max_dims=4,
            min_side=2,
            max_side=3,
        ),
        e(
            "broadcastable_shapes",  # min_side too large
            shape=(0, 1),
            min_dims=2,
            max_dims=4,
            min_side=2,
            max_side=3,
        ),
        e(
            "broadcastable_shapes",  # default max_dims unsatisfiable
            shape=(5, 3, 2, 1),
            min_dims=3,
            max_dims=None,
            min_side=2,
            max_side=3,
        ),
        e(
            "broadcastable_shapes",  # default max_dims unsatisfiable
            shape=(0, 3, 2, 1),
            min_dims=3,
            max_dims=None,
            min_side=2,
            max_side=3,
        ),
        e("mutually_broadcastable_shapes", num_shapes=0),
        e("mutually_broadcastable_shapes", num_shapes="a"),
        e("mutually_broadcastable_shapes", num_shapes=2, base_shape="a"),
        e(
            "mutually_broadcastable_shapes",  # min_side is invalid type
            num_shapes=2,
            min_side="a",
        ),
        e(
            "mutually_broadcastable_shapes",  # min_dims is invalid type
            num_shapes=2,
            min_dims="a",
        ),
        e(
            "mutually_broadcastable_shapes",  # max_side is invalid type
            num_shapes=2,
            max_side="a",
        ),
        e(
            "mutually_broadcastable_shapes",  # max_side is invalid type
            num_shapes=2,
            max_dims="a",
        ),
        e(
            "mutually_broadcastable_shapes",  # min_side is out of domain
            num_shapes=2,
            min_side=-1,
        ),
        e(
            "mutually_broadcastable_shapes",  # min_dims is out of domain
            num_shapes=2,
            min_dims=-1,
        ),
        e(
            "mutually_broadcastable_shapes",  # max_side < min_side
            num_shapes=2,
            min_side=1,
            max_side=0,
        ),
        e(
            "mutually_broadcastable_shapes",  # max_dims < min_dims
            num_shapes=2,
            min_dims=1,
            max_dims=0,
        ),
        e(
            "mutually_broadcastable_shapes",  # max_side too small
            num_shapes=2,
            base_shape=(5, 1),
            min_dims=2,
            max_dims=4,
            min_side=2,
            max_side=3,
        ),
        e(
            "mutually_broadcastable_shapes",  # min_side too large
            num_shapes=2,
            base_shape=(0, 1),
            min_dims=2,
            max_dims=4,
            min_side=2,
            max_side=3,
        ),
        e(
            "mutually_broadcastable_shapes",  # user-specified max_dims unsatisfiable
            num_shapes=1,
            base_shape=(5, 3, 2, 1),
            min_dims=3,
            max_dims=4,
            min_side=2,
            max_side=3,
        ),
        e(
            "mutually_broadcastable_shapes",  # user-specified max_dims unsatisfiable
            num_shapes=2,
            base_shape=(0, 3, 2, 1),
            min_dims=3,
            max_dims=4,
            min_side=2,
            max_side=3,
        ),
        e("indices", shape=0),
        e("indices", shape=("1", "2")),
        e("indices", shape=(0, -1)),
        e("indices", shape=(0, 0), allow_newaxis=None),
        e("indices", shape=(0, 0), allow_ellipsis=None),
        e("indices", shape=(0, 0), min_dims=-1),
        e("indices", shape=(0, 0), min_dims=1.0),
        e("indices", shape=(0, 0), max_dims=-1),
        e("indices", shape=(0, 0), max_dims=1.0),
        e("indices", shape=(0, 0), min_dims=2, max_dims=1),
        e("indices", shape=(3, 3, 3), min_dims=4),
        e("indices", shape=(3, 3, 3), max_dims=5),
        e("indices", shape=5, min_dims=0),
        e("indices", shape=(5,), min_dims=2),
        e("indices", shape=(5,), max_dims=2),
    ],
)
def test_raise_invalid_argument(xp, xps, strat_name, kwargs):
    """Strategies raise helpful error with invalid arguments."""
    strat_func = getattr(xps, strat_name)
    strat = strat_func(**kwargs)
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(strat)


@pytest.mark.parametrize("api_version", [..., "latest", "1970.01", 42])
def test_make_strategies_namespace_raise_invalid_argument(xp, api_version):
    """Function raises helpful error with invalid arguments."""
    with pytest.raises(InvalidArgument):
        make_strategies_namespace(xp, api_version=api_version)
