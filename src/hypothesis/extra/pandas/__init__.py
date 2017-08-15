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

import pandas
import numpy as np
import hypothesis.strategies as st
import hypothesis.extra.numpy as npst
from hypothesis.errors import InvalidArgument


def is_sequence(c):
    return hasattr(c, '__len__') and hasattr(c, '__getitem__')


@st.composite
def series(
    draw, elements=None, dtype=None, index=None, min_size=0, max_size=None
):
    """
    Provides a strategy for producing a pandas.Series.

    Arguments:

    -- elements is a strategy that will be used to generate the individual
       values in the series. If None, we will attempt to infer a suitable
       default from the dtype.
    -- dtype is the numpy.dtype of the resulting series and may be any value
       that can be passed to numpy.dtype. It may also be a strategy. If so, a
       value will be drawn from it before converting to a dtype.
    -- index may be a sequence or a strategy for generating a sequence. It will
       be used as the index for the resulting series. When it is longer than
       the result it will be truncated to the right side. If None, no index
       will be passed when creating the Series and the default behaviour of
       pandas.Series will be used.
    -- min_size is the minimum number of entries in the resulting Series.
    -- max_size is the maximum number of entries in the resulting Series.
       If an explicit index is provided then max_size may be at most the
       length of the index. If an index strategy is provided then whenever the
       drawn index is too short max_size will merely be reduced.
    """

    st.check_valid_interval(
        min_size, max_size, 'min_size', 'max_size'
    )

    if isinstance(index, st.SearchStrategy):
        index = draw(index)
        index_from_strategy = True
    else:
        index_from_strategy = False

    if index is not None:
        if not is_sequence(index):
            raise InvalidArgument(
                "%s was %r of type %s, but expected a sequence" % (
                    "Result of index strategy" if index_from_strategy
                    else "index argument",
                    index, type(index).__name__
                )
            )

        if max_size is None:
            max_size = len(index)
        elif index_from_strategy:
            max_size = min(max_size, max_size)
        else:
            raise InvalidArgument((
                "Provided index %r only has %d elements, which is not "
                "enough for the provided max_size of %d. Either increase "
                "the number of elements in the index or reduce or remove "
                "the max_size argument.") % (
                    index, len(index), max_size
                ))

    if max_size is None:
        max_size = 10

    if isinstance(dtype, st.SearchStrategy):
        dtype = draw(dtype)

    dtype = np.dtype(dtype)

    if elements is None:
        elements = npst.from_dtype(dtype)

    result_data = draw(npst.arrays(
        elements=elements,
        dtype=dtype,
        shape=draw(st.integers(min_size, max_size))
    ))

    return pandas.Series(
        result_data,
        None if index is None else index[:len(result_data)]
    )
