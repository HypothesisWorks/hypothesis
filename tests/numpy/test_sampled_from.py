# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

from hypothesis import given
from tests.common.utils import checks_deprecated_behaviour
from hypothesis.strategies import sampled_from

a_numpy_array = np.array([1, 2, 3])

a_multi_dimensional_numpy_array = np.array([[1, 2, 3], [4, 5, 6]])


@given(sampled_from(a_numpy_array))
def test_can_sample_numpy_array_without_warning(member):
    assert member in a_numpy_array


@checks_deprecated_behaviour
def test_multi_dimensional_arrays_are_a_no():
    @given(sampled_from(a_multi_dimensional_numpy_array))
    def test(member):
        assert member in a_multi_dimensional_numpy_array

    test()
