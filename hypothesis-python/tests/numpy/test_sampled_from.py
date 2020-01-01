# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

from hypothesis import given
from hypothesis.errors import InvalidArgument
from hypothesis.extra import numpy as npst
from hypothesis.strategies import data, sampled_from
from tests.common.utils import fails_with


@given(
    data(), npst.arrays(dtype=npst.scalar_dtypes(), shape=npst.array_shapes(max_dims=1))
)
def test_can_sample_1D_numpy_array_without_warning(data, arr):
    data.draw(sampled_from(arr))


@fails_with(InvalidArgument)
@given(
    data(),
    npst.arrays(
        dtype=npst.scalar_dtypes(), shape=npst.array_shapes(min_dims=2, max_dims=5)
    ),
)
def test_sampling_multi_dimensional_arrays_is_deprecated(data, arr):
    data.draw(sampled_from(arr))
