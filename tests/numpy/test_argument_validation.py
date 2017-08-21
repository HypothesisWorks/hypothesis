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

import pytest
from hypothesis.errors import InvalidArgument
import hypothesis.extra.numpy as nps
import hypothesis.strategies as st


def e(a, **kwargs):
    return (a, kwargs)


@pytest.mark.parametrize(
    ('function', 'kwargs'), [
        e(nps.array_dtypes, min_size=2, max_size=1),
        e(nps.array_shapes, min_side=2, max_side=1),
        e(nps.array_shapes, min_dims=3, max_dims=2),
        e(nps.arrays, dtype=object, shape=1),
        e(nps.arrays, dtype=object, shape=(), elements=st.none()),
        e(nps.byte_string_dtypes, min_len=-1),
        e(nps.byte_string_dtypes, min_len=2, max_len=1),
        e(nps.unicode_string_dtypes, min_len=-1),
        e(nps.unicode_string_dtypes, min_len=2, max_len=1),
    ]
)
def test_raise_invalid_argument(function, kwargs):
    with pytest.raises(InvalidArgument):
        function(**kwargs).example()
