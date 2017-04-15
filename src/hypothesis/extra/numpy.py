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

import hypothesis.strategies as st
from hypothesis import settings
from hypothesis.errors import InvalidArgument
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.internal.compat import hrange, text_type, binary_type
from hypothesis.internal.reflection import proxies

TIME_RESOLUTIONS = tuple('Y  M  D  h  m  s  ms  us  ns  ps  fs  as'.split())


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


def check_argument(condition, fail_message, *f_args, **f_kwargs):
    if not condition:
        raise InvalidArgument(fail_message.format(*f_args, **f_kwargs))


def order_check(name, floor, small, large):
    if floor is None:
        floor = -np.inf
    if floor > small > large:
        check_argument(u'min_{name} was {}, must be at least {} and not more '
                       u'than max_{name} (was {})', small, floor, large,
                       name=name, condition=False)


class ArrayStrategy(SearchStrategy):

    def __init__(self, element_strategy, shape, dtype):
        self.shape = tuple(shape)
        check_argument(shape,
                       u'Array shape must have at least one dimension, '
                       u'provided shape was {}', shape)
        check_argument(all(isinstance(s, int) for s in shape),
                       u'Array shape must be integer in each dimension, '
                       u'provided shape was {}', shape)
        self.array_size = np.prod(shape)
        buff_size = settings.default.buffer_size
        check_argument(
            self.array_size * dtype.itemsize <= buff_size,
            u'Insufficient bytes of entropy to draw requested array.  '
            u'shape={}, dtype={}.  Can you reduce the size or dimensions '
            u'of the array?  What about using a smaller dtype?  If slow '
            u'test runs and minimisation are acceptable, you  could '
            u'increase settings().buffer_size from {} to at least {}.',
            shape, dtype, buff_size, self.array_size * buff_size)
        self.dtype = dtype
        self.element_strategy = element_strategy

    def do_draw(self, data):
        result = np.empty(dtype=self.dtype, shape=self.array_size)
        for i in hrange(self.array_size):
            result[i] = self.element_strategy.do_draw(data)
        return result.reshape(self.shape)


def is_scalar(spec):
    return spec in (
        int, bool, text_type, binary_type, float, complex
    )


@st.composite
def arrays(draw, dtype, shape, elements=None):
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

    .. warning::
        Hypothesis works really well with NumPy, but is designed for small
        data.  The default entropy is 8192 bytes - it is impossible to draw
        an example where ``example_array.nbytes`` is greater than
        ``settings.default.buffer_size``.
        See the :doc:`settings documentation <settings>` if you need to
        increase this value, but be aware that Hypothesis may take much
        longer to produce a minimal failure case.

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
    return draw(ArrayStrategy(elements, shape, dtype))


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
                   u'Unknown endianness: was {}, must be in {}', valid_endian)
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
    return dtype_factory('u', list(range(min_len, max_len + 1)),
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
