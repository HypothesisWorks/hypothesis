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

from collections import Counter, Iterable

import numpy as np

import pandas
import hypothesis.strategies as st
import hypothesis.extra.numpy as npst
from hypothesis.errors import InvalidArgument
from hypothesis.internal.compat import hrange, int_to_text, integer_types


def is_sequence(c):
    return hasattr(c, '__len__') and hasattr(c, '__getitem__')


def is_category_dtype(dtype):
    # We need to explicitly check that this is not a dtype because a
    # numpy dtype compared to a string will try to convert it to an
    # numpy dtype and error if it can't.
    if isinstance(dtype, np.dtype):
        return False
    return dtype == 'category'


def build_index(draw, index, min_size, max_size):
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
            max_size = min(max_size, len(index))
        else:
            raise InvalidArgument((
                'Provided index %r only has %d elements, which is not '
                'enough for the provided max_size of %d. Either increase '
                'the number of elements in the index or reduce or remove '
                'the max_size argument.') % (
                    index, len(index), max_size
            ))

    if max_size is None:
        max_size = max(10, min_size + 1)

    size = draw(st.integers(min_size, max_size))

    if index is None:
        index = hrange(size)
    else:
        assert len(index) >= size
        index = index[:size]

    return index


def dtype_for_elements_strategy(s):
    return st.shared(
        s.map(lambda x: pandas.Series([x]).dtype),
        key=('hypothesis.extra.pandas.dtype_for_elements_strategy', s),
    )


@st.composite
def series(
    draw, elements=None, dtype=None, index=None, min_size=0, max_size=None,
):
    """Provides a strategy for producing a pandas.Series.

    Arguments:

        elements: a strategy that will be used to generate the individual
            values in the series. If None, we will attempt to infer a suitable
            default from the dtype.

        dtype: the numpy.dtype of the resulting series and may be any value
            that can be passed to numpy.dtype. If None, will use pandas'
            standard behaviour to infer it from the type of the elements
            values. Note that if the type of values that comes out of your
            elements strategy varies, then so will the resulting dtype of the
            series.

        index: a sequence or a strategy for generating a sequence. It will
            be used as the index for the resulting series. When it is longer
            than
            the result it will be truncated to the right side. If None, no
            index will be passed when creating the Series and the default
            behaviour of pandas.Series will be used.

        min_size: the minimum number of entries in the resulting Series.

        max_size: the maximum number of entries in the resulting Series.
            If an explicit index is provided then max_size may be at most the
            length of the index. If an index strategy is provided then whenever
            the drawn index is too short max_size will merely be reduced.

    """

    index = build_index(
        draw, index, min_size, max_size
    )

    if elements is None and dtype is None:
        raise InvalidArgument(
            'series require either an elements strategy or a dtype.'
        )

    size = len(index)

    if dtype is not None:
        if is_category_dtype(dtype):
            numpy_dtype = np.dtype(object)
            pandas_dtype = dtype
        else:
            numpy_dtype = np.dtype(dtype)
            pandas_dtype = None

        if elements is None:
            elements = npst.from_dtype(numpy_dtype)

        result_data = draw(npst.arrays(
            elements=elements,
            dtype=numpy_dtype,
            shape=size
        ))
    else:
        result_data = draw(
            st.lists(elements, min_size=size, max_size=size)
        )
        if not result_data:
            pandas_dtype = draw(
                dtype_for_elements_strategy(elements),
            )
        else:
            pandas_dtype = None

    return pandas.Series(result_data, index, dtype=pandas_dtype)


class column(object):
    """Simple data object for describing a column in a DataFrame."""

    def __init__(self, name=None, dtype=None, elements=None):
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
        if dtype is None and elements is None:
            raise InvalidArgument(
                'At least one of dtype and elements must not be provided'
            )
        if is_category_dtype(dtype) and elements is None:
            raise InvalidArgument(
                'Must provide an elements strategy for category dtypes'
            )

    def __repr__(self):
        return 'column(%r, dtype=%r, elements=%r)' % (
            self.name, self.dtype, self.elements,
        )


def columns(names_or_number, dtype=None, elements=None):
    st.check_type(
        (Iterable,) + integer_types, names_or_number, 'names_or_number'
    )
    try:
        names = list(names_or_number)
    except TypeError:
        names = [None] * names_or_number
    return [
        column(name=n, dtype=dtype, elements=elements) for n in names
    ]


@st.composite
def data_frames(
    draw,
    rows_or_columns=None,
    columns=None, rows=None, index=None, min_size=0, max_size=None
):
    """Provides a strategy for producing a pandas.DataFrame.

    Arguments:
        rows_or_columns: A special argument designed for convenient use as a
        positional argument. It will be passed as one of the rows or columns
        arguments according to the following rules:

        * An error is raised if all three of rows_or_columns, rows and columns
          are not None.
        * If rows_or_columns is not None and one of rows or columns is not None
          then rows_or_columns will be passed as the other.
        * If rows_or_columns is not None and rows and columns are both None
          then the type of the value passed will be used. If it is a strategy
          then it will be passed as rows, else it will be passed as columns.

        columns: An iterable of column objects describing the shape of the
            generated DataFrame.

        rows: A strategy for generating a row object. Should generate anything
            that could be passed to pandas as a list - e.g. dicts, tuples.

            At least one of rows and columns must be provided. If both are
            provided then the generated rows will be validated against the
            columns and an error will be raised if they don't match.

            Caveats on using rows:

            * In general you should prefer using columns to rows, and only use
              rows if the columns interface is insufficiently flexible to
              describe what you need - you will get better performance and
              example quality that way.
            * If you provide rows and not columns, then the shape and dtype of
              the resulting DataFrame may vary. e.g. if you have a mix of int
              and float in the values for one column in your row entries, the
              resulting DataFrame will sometimes have an integral dtype and
              sometimes a float.

        index: a sequence or a strategy for generating a sequence. It will
            be used as the index for the resulting series. When it is longer
            than the result it will be truncated to the right side.

        min_size: the minimum number of entries in the resulting DataFrame.

        max_size: the maximum number of entries in the resulting DataFrame.
            If an explicit index is provided then max_size may be at most the
            length of the index. If an index strategy is provided then whenever
            the drawn index is too short max_size will merely be reduced.

    """

    index = build_index(
        draw, index, min_size, max_size
    )

    if rows_or_columns is not None:
        if rows is not None:
            if columns is not None:
                raise InvalidArgument(
                    'At most two of rows, columns, and rows_or_columns can be '
                    'provided.'
                )
            else:
                columns = rows_or_columns
        elif columns is not None or isinstance(
            rows_or_columns, st.SearchStrategy
        ):
            rows = rows_or_columns
        else:
            columns = rows_or_columns

    if columns is None:
        if rows is None:
            raise InvalidArgument(
                'At least one of rows and columns must be provided'
            )

        if len(index) > 0:
            return pandas.DataFrame(
                [draw(rows) for _ in index],
                index=index
            )
        else:
            # If we haven't drawn any rows we need to draw one row and then
            # discard it so that we get a consistent shape for the the
            # DataFrame.
            base = draw(st.shared(
                rows.map(lambda x: pandas.DataFrame([x])),
                key=('hypothesis.extra.pandas.row_shape', rows),
            ))
            return base.drop(0)

    column_names = []
    datatype_elements = []
    strategies = []
    categorical_columns = []

    for i, c in enumerate(columns):
        st.check_type(column, c, 'columns[%d]' % (i,))
        name = c.name
        if name is None:
            # FIXME: Need a plan for properly handling non-string column names.
            name = int_to_text(i)
        dtype = c.dtype
        elements = c.elements
        if dtype is None:
            dtype = draw(dtype_for_elements_strategy(elements))
        if is_category_dtype(dtype):
            dtype = np.dtype(object)
            categorical_columns.append(name)
        else:
            dtype = np.dtype(dtype)

        if elements is None:
            elements = npst.from_dtype(dtype)

        column_names.append(name)
        strategies.append(elements)
        datatype_elements.append((name, dtype))

    if len(set(column_names)) < len(column_names):
        counts = Counter(column_names)
        raise InvalidArgument(
            'columns definition contains duplicate column names: %r' % (
                sorted(c for c, n in counts.items() if n > 1)))

    structured_dtype = np.dtype(datatype_elements)

    if rows is None:
        result_data = draw(npst.arrays(
            elements=st.tuples(*strategies),
            dtype=structured_dtype,
            shape=len(index),
        ))

        assert result_data.dtype == structured_dtype

        result = pandas.DataFrame(
            result_data, index=index
        )
    else:
        result = pandas.DataFrame(np.zeros(
            dtype=structured_dtype,
            shape=len(index)), index=index)

        for i in hrange(len(index)):
            result.iloc[i] = draw(rows)

    assert len(result.columns) == len(column_names)

    for c in categorical_columns:
        result[c] = result[c].astype('category')
    return result
