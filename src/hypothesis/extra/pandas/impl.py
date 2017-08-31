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

from copy import copy
from collections import OrderedDict

import attr
import numpy as np

import pandas
import hypothesis.strategies as st
import hypothesis.extra.numpy as npst
import hypothesis.internal.conjecture.utils as cu
from pandas.api.types import is_categorical_dtype
from hypothesis.errors import InvalidArgument
from hypothesis.internal.compat import hrange
from hypothesis.internal.branchcheck import check, check_function
from hypothesis.control import reject


def dtype_for_elements_strategy(s):
    return st.shared(
        s.map(lambda x: pandas.Series([x]).dtype),
        key=('hypothesis.extra.pandas.dtype_for_elements_strategy', s),
    )


def infer_dtype_if_necessary(dtype, values, elements, draw):
    if dtype is None and not values:
        return draw(dtype_for_elements_strategy(elements))
    return dtype


@check_function
def elements_and_dtype(elements, dtype, source=None):

    if source is None:
        prefix = ''
    else:
        prefix = '%s.' % (source,)

    if elements is not None:
        st.check_strategy(elements, '%selements' % (prefix,))
    else:
        with check('dtype is not None'):
            if dtype is None:
                raise InvalidArgument((
                    'At least one of %(prefix)selements or %(prefix)sdtype '
                    'must be provided.') % {'prefix': prefix})

    with check('is_categorical_dtype'):
        if is_categorical_dtype(dtype):
            raise InvalidArgument(
                '%sdtype is categorical, which is currently unsupported' % (
                    prefix,
                ))

    dtype = st.try_convert(np.dtype, dtype, 'dtype')

    if elements is None:
        elements = npst.from_dtype(dtype)
    elif dtype is not None:
        def convert_element(value):
            name = 'draw(%selements)' % (prefix,)
            try:
                return np.array([value], dtype=dtype)[0]
            except TypeError:
                raise InvalidArgument(
                    'Cannot convert %s=%r of type %s to dtype %s' % (
                        name, value, type(value).__name__, dtype.str
                    )
                )
            except ValueError:
                raise InvalidArgument(
                    'Cannot convert %s=%r to type %s' % (
                        name, value, dtype.str,
                    )
                )
        elements = elements.map(convert_element)
    assert elements is not None

    return elements, dtype


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

        while iterator.more():
            elt = data.draw(self.elements)

            if self.unique:
                if elt in seen:
                    iterator.reject()
                    continue
                seen.add(elt)
            result.append(elt)

        dtype = infer_dtype_if_necessary(
            dtype=self.dtype, values=result, elements=self.elements,
            draw=data.draw
        )
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


@st.defines_strategy
def series(elements=None, dtype=None, index=None, fill=None, unique=False):
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

    elements, dtype = elements_and_dtype(elements, dtype)
    index_strategy = index

    @st.composite
    def result(draw):
        index = draw(index_strategy)

        if len(index) > 0:
            if dtype is not None:
                result_data = draw(npst.arrays(
                    dtype=dtype, elements=elements, shape=len(index),
                    fill=fill, unique=unique,
                ))
            else:
                result_data = list(draw(npst.arrays(
                    dtype=object, elements=elements, shape=len(index),
                    fill=fill, unique=unique,
                )))

            return pandas.Series(
                result_data, index=index, dtype=dtype
            )
        else:
            return pandas.Series(
                (), index=index,
                dtype=dtype if dtype is not None else draw(
                    dtype_for_elements_strategy(elements)))

    return result()


@attr.s(slots=True)
class column(object):
    """Simple data object for describing a column in a DataFrame.

    Arguments:

    * name: the column name, or None to default to the column position. Must
      be hashable, but can otherwise be any value supported as a pandas column
      name.
    * elements: the strategy for generating values in this column, or None
      to infer it from the dtype.
    * dtype: the dtype of the column, or None to infer it from the element
      strategy. At least one of dtype or elements must be provided.
    * fill: A default value for elements of the column. See
      :func:`~hypothesis.extra.numpy.arrays` for a full explanation.
    * unique: If all values in this column should be distinct.

    """

    name = attr.ib(default=None)
    elements = attr.ib(default=None)
    dtype = attr.ib(default=None)
    fill = attr.ib(default=None)
    unique = attr.ib(default=False)


def columns(
    names_or_number, dtype=None, elements=None, fill=None, unique=False
):
    """A convenience function for producing a list of :class:`column` objects
    of the same general shape.

    The names_or_number argument is either a sequence of values, the
    elements of which will be used as the name for individual column
    objects, or a number, in which case that many unnamed columns will
    be created. All other arguments are passed through verbatim to
    create the columns.

    """
    try:
        names = list(names_or_number)
    except TypeError:
        names = [None] * names_or_number
    return [
        column(
            name=n, dtype=dtype, elements=elements, fill=fill, unique=unique
        ) for n in names
    ]


@check_function
def fill_for(elements, unique, fill, name=''):
    # FIXME: Move to hypothesis.extra.numpy
    if fill is None:
        if unique or not elements.has_reusable_values:
            fill = st.nothing()
        else:
            fill = elements
    else:
        st.check_strategy(fill, '%s.fill' % (name,) if name else 'fill')
    return fill


@st.defines_strategy
def data_frames(
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

    index_strategy = index

    if columns is None:
        if rows is None:
            raise InvalidArgument(
                'At least one of rows and columns must be provided'
            )
        else:
            @st.composite
            def rows_only(draw):
                index = draw(index_strategy)
                if len(index) > 0:
                    return pandas.DataFrame(
                        [draw(rows) for _ in index],
                        index=index
                    )
                else:
                    # If we haven't drawn any rows we need to draw one row and
                    # then discard it so that we get a consistent shape for the
                    # DataFrame.
                    base = draw(st.shared(
                        rows.map(lambda x: pandas.DataFrame([x])),
                        key=('hypothesis.extra.pandas.row_shape', rows),
                    ))
                    return base.drop(0)
            return rows_only()

    assert columns is not None
    columns = st.try_convert(tuple, columns, 'columns')

    rewritten_columns = []
    column_names = set()

    for i, c in enumerate(columns):
        st.check_type(column, c, 'columns[%d]' % (i,))

        c = copy(c)
        if c.name is None:
            label = 'columns[%d]' % (i,)
            c.name = i
        else:
            label = c.name
            try:
                hash(c.name)
            except TypeError:
                raise InvalidArgument(
                    'Column names must be hashable, but columns[%d].name was '
                    '%r of type %s, which cannot be hashed.' % (
                        i, c.name, type(c.name).__name__,))

        if c.name in column_names:
            raise InvalidArgument(
                'duplicate definition of column name %r' % (c.name,))

        column_names.add(c.name)

        c.elements, c.dtype = elements_and_dtype(
            c.elements, c.dtype, label
        )

        c.fill = fill_for(
            fill=c.fill, elements=c.elements, unique=c.unique,
            name=label
        )

        rewritten_columns.append(c)

    if rows is None:
        @st.composite
        def just_draw_columns(draw):
            index = draw(index_strategy)
            local_index_strategy = st.just(index)

            data = OrderedDict((c.name, None) for c in rewritten_columns)

            # Depending on how the columns are going to be generated we group
            # them differently to get better shrinking. For columns with fill
            # enabled, the elements can be shrunk independently of the size,
            # so we can just shrink by shrinking the index then shrinking the
            # length and are generally much more free to move data around.

            # For columns with no filling the problem is harder, and drawing
            # them like that would result in rows being very far apart from
            # eachother in the underlying data stream, which gets in the way
            # of shrinking. So what we do is reorder and draw those columns
            # row wise, so that the values of each row are next to each other.
            # This makes life easier for the shrinker when deleting blocks of
            # data.
            columns_without_fill = [
                c for c in rewritten_columns if c.fill.is_empty]

            if columns_without_fill:
                for c in columns_without_fill:
                    data[c.name] = pandas.Series(
                        np.zeros(shape=len(index), dtype=c.dtype),
                        index=index,
                    )
                seen = {
                    c.name: set() for c in columns_without_fill if c.unique}

                for i in hrange(len(index)):
                    for c in columns_without_fill:
                        if c.unique:
                            for _ in range(5):
                                value = draw(c.elements)
                                if value not in seen[c.name]:
                                    seen[c.name].add(value)
                                    break
                            else:
                                reject()
                        else:
                            value = draw(c.elements)
                        data[c.name][i] = value

            for c in rewritten_columns:
                if not c.fill.is_empty:
                    data[c.name] = draw(series(
                        index=local_index_strategy, dtype=c.dtype,
                        elements=c.elements, fill=c.fill, unique=c.unique))

            return pandas.DataFrame(data, index=index)
        return just_draw_columns()
    else:
        @st.composite
        def assign_rows(draw):
            index = draw(index_strategy)

            result = pandas.DataFrame(OrderedDict(
                (c.name, pandas.Series(
                    np.zeros(dtype=c.dtype, shape=len(index)), dtype=c.dtype))
                for c in rewritten_columns
            ), index=index)

            fills = {}

            for row_index in hrange(len(index)):
                row = draw(rows)
                if isinstance(row, dict):
                    as_list = [None] * len(rewritten_columns)
                    for i, c in enumerate(rewritten_columns):
                        try:
                            as_list[i] = row[c.name]
                        except KeyError:
                            try:
                                as_list[i] = fills[i]
                            except KeyError:
                                fills[i] = draw(c.fill)
                                as_list[i] = fills[i]
                    for k in row:
                        if k not in column_names:
                            raise InvalidArgument((
                                'Row %r contains column %r not in '
                                'columns %r)' % (
                                    row, k, [
                                        c.name for c in rewritten_columns
                                    ])))
                    row = as_list
                result.iloc[row_index] = row
            return result
        return assign_rows()
