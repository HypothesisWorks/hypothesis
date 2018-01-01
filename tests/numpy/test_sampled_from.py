# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import numpy as np

from hypothesis import given, assume
from hypothesis.extra import numpy as npst
from tests.common.utils import checks_deprecated_behaviour
from hypothesis.strategies import data, sampled_from


@given(data(), npst.arrays(
    dtype=npst.scalar_dtypes(),
    shape=npst.array_shapes(max_dims=1)
))
def test_can_sample_1D_numpy_array_without_warning(data, arr):
    elem = data.draw(sampled_from(arr))
    try:
        assume(not np.isnan(elem))
    except TypeError:
        pass
    assert elem in arr


@checks_deprecated_behaviour
@given(data(), npst.arrays(
    dtype=npst.scalar_dtypes(),
    shape=npst.array_shapes(min_dims=2, max_dims=5)
))
def test_sampling_multi_dimensional_arrays_is_deprecated(data, arr):
    data.draw(sampled_from(arr))
