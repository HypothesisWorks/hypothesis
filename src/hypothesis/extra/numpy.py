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

import math
from collections import Iterable

import numpy as np

import hypothesis.strategies as st
import hypothesis.internal.conjecture.utils as cu
from hypothesis.errors import InvalidArgument
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.internal.compat import hrange, text_type
from hypothesis.internal.reflection import proxies
from hypothesis.internal.branchcheck import check_function

TIME_RESOLUTIONS = tuple('Y  M  D  h  m  s  ms  us  ns  ps  fs  as'.split())


@st.defines_strategy_with_reusable_values
def from_dtype(dtype):
    # Compound datatypes, eg 'f4,f4,f4'
    if dtype.names is not None:
        # mapping np.void.type over a strategy is nonsense, so return now.
        return st.tuples(
            *[from_dtype(dtype.fields[name][0]) for name in dtype.names])

    # Subarray datatypes, eg '(2, 3)i4'
    if dtype.subdtype is not None:
        subtype, shape = dtype.subdtype
        return arrays(subtype, shape)

    # Scalar datatypes
    if dtype.kind == u'b':
        result = st.booleans()
    elif dtype.kind == u'f':
        result = st.floats()
    elif dtype.kind == u'c':
        result = st.complex_numbers()
    elif dtype.kind in (u'S', u'a'):
        result = st.binary()
    elif dtype.kind == u'u':
        result = st.integers(
            min_value=0, max_value=1 << (4 * dtype.itemsize) - 1)
    elif dtype.kind == u'i':
        min_integer = -1 << (4 * dtype.itemsize - 1)
        result = st.integers(min_value=min_integer, max_value=-min_integer - 1)
    elif dtype.kind == u'U':
        result = st.text()
    elif dtype.kind in (u'm', u'M'):
        res = st.just(dtype.str[-2]) if '[' in dtype.str else \
            st.sampled_from(TIME_RESOLUTIONS)
        result = st.builds(dtype.type, st.integers(1 - 2**63, 2**63 - 1), res)
    else:
        raise InvalidArgument(u'No strategy inference for {}'.format(dtype))
    return result.map(dtype.type)


@check_function
def check_argument(condition, fail_message, *f_args, **f_kwargs):
    if not condition:
        raise InvalidArgument(fail_message.format(*f_args, **f_kwargs))


@check_function
def order_check(name, floor, small, large):
    check_argument(
        floor <= small, u'min_{name} must be at least {} but was {}',
        floor, small, name=name
    )
    check_argument(
        small <= large, u'min_{name}={} is larger than max_name={}',
        small, large, name=name
    )


class FillValue(object):
    """A FillValue specifies how to provide the base value that is used to fill
    a generated array.

    See :func:`~hypothesis.extra.numpy.arrays` for details.

    """

    infer = 1
    draw = 2
    no_fill = 3


class ArrayStrategy(SearchStrategy):

    def __init__(self, element_strategy, shape, dtype, fill_value):
        self.shape = tuple(shape)
        self.fill_value = fill_value
        check_argument(shape,
                       u'Array shape must have at least one dimension, '
                       u'provided shape was {}', shape)
        check_argument(all(isinstance(s, int) for s in shape),
                       u'Array shape must be integer in each dimension, '
                       u'provided shape was {}', shape)
        self.array_size = np.prod(shape)
        self.dtype = dtype
        self.element_strategy = element_strategy

    def __create_base_array(self, base):
        """Create an array of the right size which is just a copy of base."""

        if isinstance(base, Iterable):
            result = np.zeros(shape=self.array_size, dtype=self.dtype)
            for i in hrange(len(result)):
                result[i] = base
            return result.reshape(self.shape)
        else:
            return np.full(
                shape=self.shape, dtype=self.dtype, fill_value=base
            )

    def do_draw(self, data):
        if 0 in self.shape:
            return np.zeros(dtype=self.dtype, shape=self.shape)

        fill_value = self.fill_value

        if (
            fill_value is FillValue.infer
        ):
            if self.element_strategy.has_reusable_values:
                fill_value = FillValue.draw
            else:
                fill_value = FillValue.no_fill

        if fill_value is FillValue.draw:
            fill_value = data.draw(self.element_strategy)

        if fill_value is not FillValue.no_fill:
            assert not isinstance(fill_value, FillValue)

            # We draw numpy arrays as "sparse with an offset". We draw a single
            # value that is the background value of the array that everything
            # set to by default (we can't use zero because zero might not be a
            # valid value in the element strategy), and we then draw a
            # collection of index assignments within the array and assign
            # fresh values to those indices.

            result = self.__create_base_array(fill_value)

            elements = cu.many(
                data,
                min_size=0, max_size=self.array_size,
                # sqrt isn't chosen for any particularly principled reason. It
                # just grows reasonably quickly but sublinearly, and for small
                # arrays it represents a decent fraction of the array size.
                average_size=math.sqrt(self.array_size),
            )

            seen = set()

            while elements.more():
                key = tuple(
                    cu.integer_range(data, 0, k - 1) for k in self.shape
                )
                if key in seen:
                    elements.reject()
                    continue
                seen.add(key)
                result[key] = data.draw(self.element_strategy)
            return result
        else:
            # The values produced by our element strategy can not be reused
            # (either because they are mutable or because drawing them in
            # some way depends on things that have happened previusly), so we
            # have to fall back to the slow method.
            result = np.zeros(shape=self.array_size, dtype=self.dtype)
            for i in hrange(len(result)):
                result[i] = data.draw(self.element_strategy)
            return result.reshape(self.shape)


@st.composite
def arrays(
    draw, dtype, shape, elements=None, fill_value=FillValue.infer
):
    """`dtype` may be any valid input to ``np.dtype`` (this includes
    ``np.dtype`` objects), or a strategy that generates such values.  `shape`
    may be an integer >= 0, a tuple of length >= of such integers, or a
    strategy that generates such values.

    Arrays of specified `dtype` and `shape` are generated for example
    like this:

    .. code-block:: pycon

      >>> import numpy as np
      >>> arrays(np.int8, (2, 3)).example()
      array([[-8,  6,  3],
             [-6,  4,  6]], dtype=int8)

    If elements is None, Hypothesis infers a strategy based on the dtype,
    which may give any legal value (including eg ``NaN`` for floats).  If you
    have more specific requirements, you can supply your own elements strategy
    - see :doc:`What you can generate and how <data>`.

    .. code-block:: pycon

      >>> import numpy as np
      >>> from hypothesis.strategies import floats
      >>> arrays(np.float, 3, elements=floats(0, 1)).example()
      array([ 0.88974794,  0.77387938,  0.1977879 ])

    fill_value specifies a default element to be used for "most" of the
    elements in the array when the array is large. It may either be set to a
    value to use, or one of FillValue.infer, FillValue.draw or
    FillValue.no_fill.

    When it is set to one of these special values it has the following
    behaviour:

    1. If it is set to FillValue.draw then a single value will be drawn from
       the element strategy for the array and used for the fill value.
    2. If it is set to no_fill then no fill value will be used and every
       element of the array will be drawn from the elements strategy.
    3. If it is set to FillValue.infer (the default), Hypothesis will attempt
       to use FillValue.draw if it can tell for sure that it is appropriate,
       and if not will use FillValue.no_fill. This will result in using
       FillValue.draw for most built-in strategies and dtypes that return
       immutable types, but e.g. strategies defined using composite, flatmap,
       map or filter, or strategies that return mutable types, will default to
       FillValue.no_fill and must explicitly opt in to having a FillValue.

    Having a fill_value helps Hypothesis craft high quality examples, but its
    main importance is when the array generated is large: Hypothesis is
    primarily designed around testing small examples. If you have arrays with
    hundreds or more elements, having a fill value is essential if you want
    your tests to run in reasonable time.

    """
    if isinstance(dtype, SearchStrategy):
        dtype = draw(dtype)
    dtype = np.dtype(dtype)
    if elements is None:
        elements = from_dtype(dtype)
    if isinstance(shape, SearchStrategy):
        shape = draw(shape)
    if isinstance(shape, int):
        shape = (shape,)
    shape = tuple(shape)
    if not shape:
        if dtype.kind != u'O':
            return draw(elements)
    return draw(ArrayStrategy(elements, shape, dtype, fill_value))


@st.defines_strategy
def array_shapes(min_dims=1, max_dims=3, min_side=1, max_side=10):
    """Return a strategy for array shapes (tuples of int >= 1)."""
    order_check('dims', 1, min_dims, max_dims)
    order_check('side', 1, min_side, max_side)
    return st.lists(st.integers(min_side, max_side),
                    min_size=min_dims, max_size=max_dims).map(tuple)


@st.defines_strategy
def scalar_dtypes():
    """Return a strategy that can return any non-flexible scalar dtype."""
    return st.one_of(boolean_dtypes(),
                     integer_dtypes(), unsigned_integer_dtypes(),
                     floating_dtypes(), complex_number_dtypes(),
                     datetime64_dtypes(), timedelta64_dtypes())


def defines_dtype_strategy(strat):
    @st.defines_strategy
    @proxies(strat)
    def inner(*args, **kwargs):
        return strat(*args, **kwargs).map(np.dtype)
    return inner


@defines_dtype_strategy
def boolean_dtypes():
    return st.just('?')


def dtype_factory(kind, sizes, valid_sizes, endianness):
    # Utility function, shared logic for most integer and string types
    valid_endian = ('?', '<', '=', '>')
    check_argument(endianness in valid_endian,
                   u'Unknown endianness: was {}, must be in {}',
                   endianness, valid_endian)
    if valid_sizes is not None:
        if isinstance(sizes, int):
            sizes = (sizes,)
        check_argument(sizes, 'Dtype must have at least one possible size.')
        check_argument(all(s in valid_sizes for s in sizes),
                       u'Invalid sizes: was {} must be an item or sequence '
                       u'in {}', sizes, valid_sizes)
        if all(isinstance(s, int) for s in sizes):
            sizes = sorted(set(s // 8 for s in sizes))
    strat = st.sampled_from(sizes)
    if '{}' not in kind:
        kind += '{}'
    if endianness == '?':
        return strat.map(('<' + kind).format) | strat.map(('>' + kind).format)
    return strat.map((endianness + kind).format)


@defines_dtype_strategy
def unsigned_integer_dtypes(endianness='?', sizes=(8, 16, 32, 64)):
    """Return a strategy for unsigned integer dtypes.

    endianness may be ``<`` for little-endian, ``>`` for big-endian,
    ``=`` for native byte order, or ``?`` to allow either byte order.
    This argument only applies to dtypes of more than one byte.

    sizes must be a collection of integer sizes in bits.  The default
    (8, 16, 32, 64) covers the full range of sizes.

    """
    return dtype_factory('u', sizes, (8, 16, 32, 64), endianness)


@defines_dtype_strategy
def integer_dtypes(endianness='?', sizes=(8, 16, 32, 64)):
    """Return a strategy for signed integer dtypes.

    endianness and sizes are treated as for `unsigned_integer_dtypes`.

    """
    return dtype_factory('i', sizes, (8, 16, 32, 64), endianness)


@defines_dtype_strategy
def floating_dtypes(endianness='?', sizes=(16, 32, 64)):
    """Return a strategy for floating-point dtypes.

    sizes is the size in bits of floating-point number.  Some machines support
    96- or 128-bit floats, but these are not generated by default.

    Larger floats (96 and 128 bit real parts) are not supported on all
    platforms and therefore disabled by default.  To generate these dtypes,
    include these values in the sizes argument.

    """
    return dtype_factory('f', sizes, (16, 32, 64, 96, 128), endianness)


@defines_dtype_strategy
def complex_number_dtypes(endianness='?', sizes=(64, 128)):
    """Return a strategy complex-number dtypes.

    sizes is the total size in bits of a complex number, which consists
    of two floats.  Complex halfs (a 16-bit real part) are not supported
    by numpy and will not be generated by this strategy.

    """
    return dtype_factory('c', sizes, (64, 128, 192, 256), endianness)


@check_function
def validate_time_slice(max_period, min_period):
    check_argument(max_period in TIME_RESOLUTIONS,
                   u'max_period {} must be a valid resolution in {}',
                   max_period, TIME_RESOLUTIONS)
    check_argument(min_period in TIME_RESOLUTIONS,
                   u'min_period {} must be a valid resolution in {}',
                   min_period, TIME_RESOLUTIONS)
    start = TIME_RESOLUTIONS.index(max_period)
    end = TIME_RESOLUTIONS.index(min_period) + 1
    check_argument(start < end,
                   u'max_period {} must be earlier in sequence {} than '
                   u'min_period {}', max_period, TIME_RESOLUTIONS, min_period)
    return TIME_RESOLUTIONS[start:end]


@defines_dtype_strategy
def datetime64_dtypes(max_period='Y', min_period='ns', endianness='?'):
    """Return a strategy for datetime64 dtypes, with various precisions from
    year to attosecond."""
    return dtype_factory('datetime64[{}]',
                         validate_time_slice(max_period, min_period),
                         TIME_RESOLUTIONS, endianness)


@defines_dtype_strategy
def timedelta64_dtypes(max_period='Y', min_period='ns', endianness='?'):
    """Return a strategy for timedelta64 dtypes, with various precisions from
    year to attosecond."""
    return dtype_factory('timedelta64[{}]',
                         validate_time_slice(max_period, min_period),
                         TIME_RESOLUTIONS, endianness)


@defines_dtype_strategy
def byte_string_dtypes(endianness='?', min_len=0, max_len=16):
    """Return a strategy for generating bytestring dtypes, of various lengths
    and byteorder."""
    order_check('len', 0, min_len, max_len)
    return dtype_factory('S', list(range(min_len, max_len + 1)),
                         None, endianness)


@defines_dtype_strategy
def unicode_string_dtypes(endianness='?', min_len=0, max_len=16):
    """Return a strategy for generating unicode string dtypes, of various
    lengths and byteorder."""
    order_check('len', 0, min_len, max_len)
    return dtype_factory('U', list(range(min_len, max_len + 1)),
                         None, endianness)


@defines_dtype_strategy
def array_dtypes(subtype_strategy=scalar_dtypes(),
                 min_size=1, max_size=5, allow_subarrays=False):
    """Return a strategy for generating array (compound) dtypes, with members
    drawn from the given subtype strategy."""
    order_check('size', 0, min_size, max_size)
    native_strings = st.text if text_type is str else st.binary
    elements = st.tuples(native_strings(), subtype_strategy)
    if allow_subarrays:
        elements |= st.tuples(native_strings(), subtype_strategy,
                              array_shapes(max_dims=2, max_side=2))
    return st.lists(elements=elements, min_size=min_size, max_size=max_size,
                    unique_by=lambda d: d[0])


@st.defines_strategy
def nested_dtypes(subtype_strategy=scalar_dtypes(),
                  max_leaves=10, max_itemsize=None):
    """Return the most-general dtype strategy.

    Elements drawn from this strategy may be simple (from the
    subtype_strategy), or several such values drawn from `array_dtypes`
    with ``allow_subarrays=True``. Subdtypes in an array dtype may be
    nested to any depth, subject to the max_leaves argument.

    """
    return st.recursive(subtype_strategy,
                        lambda x: array_dtypes(x, allow_subarrays=True),
                        max_leaves).filter(
        lambda d: max_itemsize is None or d.itemsize <= max_itemsize)
