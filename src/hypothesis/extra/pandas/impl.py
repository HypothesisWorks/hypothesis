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

from collections import Counter, Iterable, OrderedDict

import numpy as np

import pandas
import hypothesis.strategies as st
import hypothesis.extra.numpy as npst
import hypothesis.internal.conjecture.utils as cu
from pandas.api.types import is_categorical_dtype
from hypothesis.errors import InvalidArgument
from hypothesis.internal.compat import hrange, integer_types
from hypothesis.internal.branchcheck import check_function


def is_sequence(c):
    return hasattr(c, '__len__') and hasattr(c, '__getitem__')


def build_index(draw, index, min_size, max_size):
    st.check_valid_interval(
        min_size, max_size, 'min_size', 'max_size'
    )

    if index is not None:
        if not is_sequence(index):
            raise InvalidArgument(
                'index=%r was of type %s, but expected a sequence' % (
                    index, type(index).__name__
                )
            )

        if max_size is not None and max_size < len(index):
            raise InvalidArgument(
                'Provided index=%r has %d items < max_size=%d' % (
                    index, len(index), max_size))
            max_size = len(index)
        if min_size is not None and min_size > len(index):
            raise InvalidArgument(
                'Provided index=%r has %d items > min_size=%d' % (
                    index, len(index), min_size))
        return index

    if max_size is None:
        max_size = min_size + 10

    return hrange(draw(st.integers(min_size, max_size)))


def dtype_for_elements_strategy(s):
    return st.shared(
        s.map(lambda x: pandas.Series([x]).dtype),
        key=('hypothesis.extra.pandas.dtype_for_elements_strategy', s),
    )


@check_function
def elements_and_dtype(elements, dtype):
    if elements is None and dtype is None:
        raise InvalidArgument(
            'At least one of elements or dtype must be provided.'
        )

    if elements is not None:
        st.check_strategy(elements, 'elements')

    dtype = st.try_convert(np.dtype, dtype, 'dtype')

    if elements is None:
        elements = npst.from_dtype(dtype)
        dtype_strategy = st.just(dtype)
    else:
        if dtype is None:
            dtype_strategy = dtype_for_elements_strategy(elements)
        else:
            def convert_element(e):
                return st.try_convert(
                    dtype.type, e, 'draw(elements)'
                )
            elements = elements.map(convert_element)
    assert elements is not None

    return elements, dtype_strategy


class ValueIndexStrategy(st.SearchStrategy):
    def __init__(self, elements, dtype, min_size, max_size, unique):
        super(ValueIndexStrategy, self).__init__()
        self.elements = elements
        self.dtype = dtype
        self.min_size = min_size
        self.max_size = max_size
        self.unique = unique

    def do_draw(self, data):
        result = []
        seen = set()

        iterator = cu.many(
            data, min_size=self.min_size, max_size=self.max_size,
            average_size=(self.min_size + self.max_size) / 2
        )

        dtype = data.draw(self.dtype)

        while iterator.more():
            elt = data.draw(self.elements)

            if self.unique:
                if elt in seen:
                    iterator.reject()
                    continue
                seen.add(elt)
            result.append(elt)

        return pandas.Index(result, dtype=dtype)


DEFAULT_MAX_SIZE = 10


@st.cacheable
@st.defines_strategy
def range_indexes(min_size=0, max_size=None):
    st.check_valid_interval(min_size, max_size, 'min_size', 'max_size')
    if max_size is None:
        max_size = min_size + DEFAULT_MAX_SIZE
    return st.integers(min_size, max_size).map(
        lambda i: pandas.Index(hrange(i), dtype=int)
    )


@st.cacheable
@st.defines_strategy
def indexes(
    elements=None, dtype=None, min_size=0, max_size=None, unique=True,
):
    """Provides a strategy for generating values of type pandas.Index.

    * elements is a strategy which will be used to generate the individual
      values of the index. If None, it will be inferred from the dtype.
    * dtype is the dtype of the resulting index. If None, it will be inferred
      from the elements strategy. At least one of dtype or elements must be
      provided.
    * min_size is the minimum number of elements in the index.
    * max_size is the maximum number of elements in the index. If None then it
      will default to a suitable small size. If you want larger indexes you
      should pass a max_size explicitly.
    * unique specifies whether all of the elements in the resulting index
      should be distinct.

    """
    st.check_valid_interval(min_size, max_size, 'min_size', 'max_size')
    st.check_type(bool, unique, 'unique')

    elements, dtype = elements_and_dtype(elements, dtype)

    if max_size is None:
        max_size = min_size + DEFAULT_MAX_SIZE
    return ValueIndexStrategy(
        elements, dtype, min_size, max_size, unique)


@st.composite
def series(
    draw, elements=None, dtype=None, index=None,
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

        index: If not None, a strategy for generating indexes for the resulting
            Series. This can generate either pandas.Index objects or any
            sequence of values (which will be passed to the pandas.Index)
            constructors.

            You will probably find it most convenient to use the
            :func:`~hypothesis.extra.pandas.indexes` function to pass as values
            for this argument.

    """
    if index is None:
        index = range_indexes()
    else:
        st.check_strategy(index)

    if elements is None and dtype is None:
        raise InvalidArgument(
            'series require either an elements strategy or a dtype.'
        )

    index = draw(index)
    size = len(index)

    if dtype is not None:
        if is_categorical_dtype(dtype):
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
        if is_categorical_dtype(dtype) and elements is None:
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
    columns=None, rows=None, index=None
):
    """Provides a strategy for producing a pandas.DataFrame.

    Arguments:
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

        index: If not None, a strategy for generating indexes for the resulting
            DataFrame. This can generate either pandas.Index objects or any
            sequence of values (which will be passed to the pandas.Index)
            constructors.

            You will probably find it most convenient to use the
            :func:`~hypothesis.extra.pandas.indexes` function to pass as values
            for this argument.

    """

    if index is None:
        index = range_indexes()
    else:
        st.check_strategy(index)

    index = draw(index)

    if isinstance(columns, column):
        columns = (columns,)

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
    dtypes = []
    strategies = []
    categorical_columns = []

    for i, c in enumerate(columns):
        st.check_type(column, c, 'columns[%d]' % (i,))
        name = c.name
        if name is None:
            name = i
        dtype = c.dtype
        elements = c.elements
        if dtype is None:
            dtype = draw(dtype_for_elements_strategy(elements))
        if is_categorical_dtype(dtype):
            dtype = np.dtype(object)
            categorical_columns.append(name)
        else:
            dtype = np.dtype(dtype)

        if elements is None:
            elements = npst.from_dtype(dtype)

        column_names.append(name)
        strategies.append(elements)
        dtypes.append(dtype)

    if len(set(column_names)) < len(column_names):
        counts = Counter(column_names)
        raise InvalidArgument(
            'columns definition contains duplicate column names: %r' % (
                sorted(c for c, n in counts.items() if n > 1)))

    zeroes = np.zeros(len(index))

    series = [
        pandas.Series(zeroes, dtype=dtype)
        for dtype in dtypes
    ]

    # FIXME: When we have the fill argument for arrays pull request merged we
    # should use np.arrays for columns where we can be sparse and only pack
    # together the rest like this.
    if rows is None:
        for i in hrange(len(index)):
            # Note: We draw one row at a time. This is important because it
            # means we can delete rows (once the new shrinker has been
            # merged).
            for j in hrange(len(series)):
                series[j][i] = draw(strategies[j])

    result = pandas.DataFrame(
        OrderedDict(zip(column_names, series)), index=index
    )

    if rows is not None:
        for i in hrange(len(index)):
            result.iloc[i] = draw(rows)

    assert len(result.columns) == len(column_names)

    for c in categorical_columns:
        result[c] = result[c].astype('category')
    return result
