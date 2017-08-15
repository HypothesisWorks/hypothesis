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
from collections import Counter


def is_sequence(c):
    return hasattr(c, '__len__') and hasattr(c, '__getitem__')


PANDAS_TIME_DTYPES = tuple(
    pandas.Series(np.array([], dtype=d)).dtype
    for d in ('datetime64', 'timedelta64')
)


def supported_by_pandas(dtype):
    """ Checks whether the dtype is one that can be correctly handled by Pandas

    We only use this where we choose the dtype. If the user chooses the dtype
    to be one that pandas doesn't fully support, they are in for an exciting
    journey of discovery.
    """

    # Pandas only supports a limited range of timedelta and datetime dtypes
    # compared to the full range that numpy supports and will convert
    # everything to those types (possibly increasing precision in the course of
    # doing so, which can cause problems if this results in something which
    # does not fit into the desired word type. As a result we want to filter
    # out any timedelta or datetime dtypes that are not of the desired types.

    if dtype.kind in ('m', 'M'):
        return dtype in PANDAS_TIME_DTYPES
    return True


def validate_index_and_bounds(draw, index, min_size, max_size):
    st.check_valid_interval(
        min_size, max_size, 'min_size', 'max_size'
    )

    index_from_strategy = False

    if isinstance(index, st.SearchStrategy):
        index = draw(index)
        index_from_strategy = True

    if index is not None:
        if not is_sequence(index):
            raise InvalidArgument(
                '%s was %r of type %s, but expected a sequence' % (
                    'Result of index strategy' if index_from_strategy
                    else 'index argument',
                    index, type(index).__name__
                )
            )

        if max_size is None:
            max_size = len(index)
        elif index_from_strategy:
            max_size = min(max_size, max_size)
        else:
            raise InvalidArgument((
                'Provided index %r only has %d elements, which is not '
                'enough for the provided max_size of %d. Either increase '
                'the number of elements in the index or reduce or remove '
                'the max_size argument.') % (
                    index, len(index), max_size
            ))

    if max_size is None:
        max_size = 10

    return index, min_size, max_size


@st.composite
def series(
    draw, elements=None, dtype=None, index=None, min_size=0, max_size=None
):
    """Provides a strategy for producing a pandas.Series.

    Arguments:

    -- elements:  a strategy that will be used to generate the individual
       values in the series. If None, we will attempt to infer a suitable
       default from the dtype.
    -- dtype: the numpy.dtype of the resulting series and may be any value
       that can be passed to numpy.dtype. It may also be a strategy. If so, a
       value will be drawn from it before converting to a dtype.
    -- index: a sequence or a strategy for generating a sequence. It will
       be used as the index for the resulting series. When it is longer than
       the result it will be truncated to the right side. If None, no index
       will be passed when creating the Series and the default behaviour of
       pandas.Series will be used.
    -- min_size: the minimum number of entries in the resulting Series.
    -- max_size: the maximum number of entries in the resulting Series.
       If an explicit index is provided then max_size may be at most the
       length of the index. If an index strategy is provided then whenever the
       drawn index is too short max_size will merely be reduced.

    """

    index, min_size, max_size = validate_index_and_bounds(
        draw, index, min_size, max_size
    )

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


class Column(object):
    """Simple data object for describing a column in a DataFrame."""

    def __init__(self, name, dtype=None, elements=None):
        """Arguments:

        -- name: the column name
        -- dtype: the dtype of the column, or None to default to float. May
            also be a strategy which will be used to generate the dtype.
        -- elements: the strategy for generating values in this column, or None
            to infer it from the dtype.

        """
        self.name = name
        self.dtype = dtype
        self.elements = elements

    def __repr__(self):
        return 'Column(%r, dtype=%r, elements=%r)' % (
            self.name, self.dtype, self.elements,
        )


def columns(names, dtype=None, elements=None):
    """Convenience function for specifying many columns of the same type."""
    return [Column(name, dtype, elements) for name in names]


@st.composite
def data_frames(
    draw, columns=None, index=None, min_size=0, max_size=None
):
    """Provides a strategy for producing a pandas.DataFrame.

    -- columns: An iterable of objects that describes the columns of the
        generated DataFrame. May also be a strategy generating such, and
        individual elements may also be strategies which will be implicitly
        drawn from.

        If an entry is a Column object then the name, dtype, and elements
        strategy will be used for generating the corresponding column.
        Otherwise it is treated as a column name and a default type of floats
        will be inferred.

        The names of columns must be distinct.

        If columns is None then random column names and datatypes will be used.

    -- index: a sequence or a strategy for generating a sequence. It will
        be used as the index for the resulting series. When it is longer than
        the result it will be truncated to the right side.
    -- min_size: the minimum number of entries in the resulting DataFrame.
    -- max_size: the maximum number of entries in the resulting DataFrame.
       If an explicit index is provided then max_size may be at most the
       length of the index. If an index strategy is provided then whenever the
       drawn index is too short max_size will merely be reduced.

    """

    index, min_size, max_size = validate_index_and_bounds(
        draw, index, min_size, max_size
    )

    def convert(s):
        if isinstance(s, st.SearchStrategy):
            return draw(s)
        else:
            return s

    if columns is None:
        columns = st.lists(
            st.builds(
                Column, st.text(),
                st.none() | npst.scalar_dtypes().filter(supported_by_pandas)
            ),
            unique_by=lambda x: x.name)

    columns = convert(columns)

    column_names = []
    datatype_elements = []
    strategies = []

    for column in columns:
        column = convert(column)
        if not isinstance(column, Column):
            name = column
            dtype = np.dtype(None)
            elements = st.floats()
        else:
            name = column.name
            dtype = np.dtype(convert(column.dtype))
            elements = column.elements or npst.from_dtype(dtype)

        column_names.append(name)
        strategies.append(elements)
        datatype_elements.append((name, dtype))

    if len(set(column_names)) < len(column_names):
        counts = Counter(column_names)
        raise InvalidArgument(
            'columns definition contains duplicate column names: %s' % (
                sorted(c for c, n in counts.items() if n > 1)))

    structured_dtype = np.dtype(datatype_elements)

    result_data = draw(npst.arrays(
        elements=st.tuples(*strategies),
        dtype=structured_dtype,
        shape=draw(st.integers(min_size, max_size)),
    ))

    assert result_data.dtype == structured_dtype

    if index is not None:
        index = index[:len(result_data)]

    return pandas.DataFrame(
        result_data, index=index
    )
