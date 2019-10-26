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

import numpy
import pytest

import hypothesis.extra.numpy as nps
import hypothesis.strategies as st
from hypothesis import given
from hypothesis.errors import InvalidArgument
from tests.common.utils import checks_deprecated_behaviour


def e(a, **kwargs):
    return (a, kwargs)


@pytest.mark.parametrize(
    ("function", "kwargs"),
    [
        e(nps.array_dtypes, min_size=2, max_size=1),
        e(nps.array_dtypes, min_size=-1),
        e(nps.array_shapes, min_side=2, max_side=1),
        e(nps.array_shapes, min_dims=3, max_dims=2),
        e(nps.array_shapes, min_dims=-1),
        e(nps.array_shapes, min_side=-1),
        e(nps.array_shapes, min_side="not an int"),
        e(nps.array_shapes, max_side="not an int"),
        e(nps.array_shapes, min_dims="not an int"),
        e(nps.array_shapes, max_dims="not an int"),
        e(nps.array_shapes, min_dims=33),
        e(nps.array_shapes, max_dims=33),
        e(nps.arrays, dtype=float, shape=(0.5,)),
        e(nps.arrays, dtype=object, shape=1),
        e(nps.arrays, dtype=float, shape=1, fill=3),
        e(nps.byte_string_dtypes, min_len=-1),
        e(nps.byte_string_dtypes, min_len=2, max_len=1),
        e(nps.datetime64_dtypes, max_period=11),
        e(nps.datetime64_dtypes, min_period=11),
        e(nps.datetime64_dtypes, min_period="Y", max_period="M"),
        e(nps.timedelta64_dtypes, max_period=11),
        e(nps.timedelta64_dtypes, min_period=11),
        e(nps.timedelta64_dtypes, min_period="Y", max_period="M"),
        e(nps.unicode_string_dtypes, min_len=-1),
        e(nps.unicode_string_dtypes, min_len=2, max_len=1),
        e(nps.unsigned_integer_dtypes, endianness=3),
        e(nps.unsigned_integer_dtypes, sizes=()),
        e(nps.unsigned_integer_dtypes, sizes=(3,)),
        e(nps.from_dtype, dtype="float64"),
        e(nps.from_dtype, dtype=float),
        e(nps.from_dtype, dtype=numpy.int8),
        e(nps.from_dtype, dtype=1),
        e(nps.valid_tuple_axes, ndim=-1),
        e(nps.valid_tuple_axes, ndim=2, min_size=-1),
        e(nps.valid_tuple_axes, ndim=2, min_size=3, max_size=10),
        e(nps.valid_tuple_axes, ndim=2, min_size=2, max_size=1),
        e(nps.valid_tuple_axes, ndim=2.0, min_size=2, max_size=1),
        e(nps.valid_tuple_axes, ndim=2, min_size=1.0, max_size=2),
        e(nps.valid_tuple_axes, ndim=2, min_size=1, max_size=2.0),
        e(nps.valid_tuple_axes, ndim=2, min_size=1, max_size=3),
        e(nps.broadcastable_shapes, shape="a"),
        e(nps.broadcastable_shapes, shape=(2, 2), min_side="a"),
        e(nps.broadcastable_shapes, shape=(2, 2), min_dims="a"),
        e(nps.broadcastable_shapes, shape=(2, 2), max_side="a"),
        e(nps.broadcastable_shapes, shape=(2, 2), max_dims="a"),
        e(nps.broadcastable_shapes, shape=(2, 2), min_side=-1),
        e(nps.broadcastable_shapes, shape=(2, 2), min_dims=-1),
        e(nps.broadcastable_shapes, shape=(2, 2), min_dims=33, max_dims=None),
        e(nps.broadcastable_shapes, shape=(2, 2), min_dims=1, max_dims=33),
        e(nps.broadcastable_shapes, shape=(2, 2), min_side=1, max_side=0),
        e(nps.broadcastable_shapes, shape=(2, 2), min_dims=1, max_dims=0),
        e(
            nps.broadcastable_shapes,  # max_side too small
            shape=(5, 1),
            min_dims=2,
            max_dims=4,
            min_side=2,
            max_side=3,
        ),
        e(
            nps.broadcastable_shapes,  # min_side too large
            shape=(0, 1),
            min_dims=2,
            max_dims=4,
            min_side=2,
            max_side=3,
        ),
        e(
            nps.broadcastable_shapes,  # default max_dims unsatisfiable
            shape=(5, 3, 2, 1),
            min_dims=3,
            max_dims=None,
            min_side=2,
            max_side=3,
        ),
        e(
            nps.broadcastable_shapes,  # default max_dims unsatisfiable
            shape=(0, 3, 2, 1),
            min_dims=3,
            max_dims=None,
            min_side=2,
            max_side=3,
        ),
        e(nps.multiple_shapes, inputs=-1),
        e(nps.multiple_shapes, inputs="a"),
        e(nps.multiple_shapes, inputs=2, base_shape="a"),
        e(nps.multiple_shapes, inputs=2, base_shape=(2, 2), min_side="a"),
        e(nps.multiple_shapes, inputs=2, base_shape=(2, 2), min_dims="a"),
        e(nps.multiple_shapes, inputs=2, base_shape=(2, 2), max_side="a"),
        e(nps.multiple_shapes, inputs=2, base_shape=(2, 2), max_dims="a"),
        e(nps.multiple_shapes, inputs=2, base_shape=(2, 2), min_side=-1),
        e(nps.multiple_shapes, inputs=2, base_shape=(2, 2), min_dims=-1),
        e(nps.multiple_shapes, inputs=2, base_shape=(2, 2), min_dims=33, max_dims=None),
        e(nps.multiple_shapes, inputs=2, base_shape=(2, 2), min_dims=1, max_dims=33),
        e(nps.multiple_shapes, inputs=2, base_shape=(2, 2), min_side=1, max_side=0),
        e(nps.multiple_shapes, inputs=2, base_shape=(2, 2), min_dims=1, max_dims=0),
        e(
            nps.multiple_shapes,
            inputs=2,  # max_side too small
            base_shape=(5, 1),
            min_dims=2,
            max_dims=4,
            min_side=2,
            max_side=3,
        ),
        e(
            nps.multiple_shapes,
            inputs=2,  # min_side too large
            base_shape=(0, 1),
            min_dims=2,
            max_dims=4,
            min_side=2,
            max_side=3,
        ),
        e(
            nps.multiple_shapes,
            inputs=2,  # default max_dims unsatisfiable
            base_shape=(5, 3, 2, 1),
            min_dims=3,
            max_dims=None,
            min_side=2,
            max_side=3,
        ),
        e(
            nps.multiple_shapes,
            inputs=2,  # default max_dims unsatisfiable
            base_shape=(0, 3, 2, 1),
            min_dims=3,
            max_dims=None,
            min_side=2,
            max_side=3,
        ),
        e(nps.basic_indices, shape=0),
        e(nps.basic_indices, shape=("1", "2")),
        e(nps.basic_indices, shape=(0, -1)),
        e(nps.basic_indices, shape=(0, 0), allow_newaxis=None),
        e(nps.basic_indices, shape=(0, 0), allow_ellipsis=None),
        e(nps.basic_indices, shape=(0, 0), min_dims=-1),
        e(nps.basic_indices, shape=(0, 0), min_dims=1.0),
        e(nps.basic_indices, shape=(0, 0), max_dims=-1),
        e(nps.basic_indices, shape=(0, 0), max_dims=1.0),
        e(nps.basic_indices, shape=(0, 0), min_dims=2, max_dims=1),
        e(nps.basic_indices, shape=(0, 0), max_dims=50),
        e(nps.integer_array_indices, shape=()),
        e(nps.integer_array_indices, shape=(2, 0)),
        e(nps.integer_array_indices, shape="a"),
        e(nps.integer_array_indices, shape=(2,), result_shape=(2, 2)),
        e(nps.integer_array_indices, shape=(2,), dtype=float),
    ],
)
def test_raise_invalid_argument(function, kwargs):
    with pytest.raises(InvalidArgument):
        function(**kwargs).example()


@nps.defines_dtype_strategy
def bad_dtype_strategy():
    return st.just([("f1", "int32"), ("f1", "int32")])


@given(st.data())
def test_bad_dtype_strategy(capsys, data):
    s = bad_dtype_strategy()
    with pytest.raises(ValueError):
        data.draw(s)
    val = s.wrapped_strategy.mapped_strategy.value
    assert capsys.readouterr().out.startswith(
        "Got invalid dtype value=%r from strategy=just(%r), function=" % (val, val)
    )


@checks_deprecated_behaviour
@given(st.data())
def test_byte_string_dtype_len_0(data):
    s = nps.byte_string_dtypes(min_len=0, max_len=0)
    assert data.draw(s).itemsize == 1


@checks_deprecated_behaviour
@given(st.data())
def test_unicode_string_dtype_len_0(data):
    s = nps.unicode_string_dtypes(min_len=0, max_len=0)
    assert data.draw(s).itemsize == 4


def test_test_basic_indices_kwonly_emulation():
    with pytest.raises(TypeError):
        nps.basic_indices((), 0, 1).validate()
    with pytest.raises(TypeError):
        nps.basic_indices((), __reserved=None).validate()
