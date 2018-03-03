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

import math

import numpy as np

import hypothesis.strategies as st
import hypothesis.internal.conjecture.utils as cu
from hypothesis.errors import InvalidArgument
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.internal.compat import hrange, text_type
from hypothesis.internal.coverage import check_function
from hypothesis.internal.reflection import proxies

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
        # Numpy strings are null-terminated; only allow round-trippable values.
        # `itemsize == 0` means 'fixed length determined at array creation'
        result = st.binary(max_size=dtype.itemsize or None
                           ).filter(lambda b: b[-1:] != b'\0')
    elif dtype.kind == u'u':
        result = st.integers(min_value=0,
                             max_value=2 ** (8 * dtype.itemsize) - 1)
    elif dtype.kind == u'i':
        overflow = 2 ** (8 * dtype.itemsize - 1)
        result = st.integers(min_value=-overflow, max_value=overflow - 1)
    elif dtype.kind == u'U':
        # Encoded in UTF-32 (four bytes/codepoint) and null-terminated
        result = st.text(max_size=(dtype.itemsize or 0) // 4 or None
                         ).filter(lambda b: b[-1:] != u'\0')
    elif dtype.kind in (u'm', u'M'):
        if '[' in dtype.str:
            res = st.just(dtype.str.split('[')[-1][:-1])
        else:
            res = st.sampled_from(TIME_RESOLUTIONS)
        result = st.builds(dtype.type, st.integers(-2**63, 2**63 - 1), res)
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
        small <= large, u'min_{name}={} is larger than max_{name}={}',
        small, large, name=name
    )


class ArrayStrategy(SearchStrategy):

    def __init__(self, element_strategy, shape, dtype, fill, unique):
        self.shape = tuple(shape)
        self.fill = fill
        check_argument(shape,
                       u'Array shape must have at least one dimension, '
                       u'provided shape was {}', shape)
        check_argument(all(isinstance(s, int) for s in shape),
                       u'Array shape must be integer in each dimension, '
                       u'provided shape was {}', shape)
        self.array_size = int(np.prod(shape))
        self.dtype = dtype
        self.element_strategy = element_strategy
        self.unique = unique

    def do_draw(self, data):
        if 0 in self.shape:
            return np.zeros(dtype=self.dtype, shape=self.shape)

        # This could legitimately be a np.empty, but the performance gains for
        # that would be so marginal that there's really not much point risking
        # undefined behaviour shenanigans.
        result = np.zeros(shape=self.array_size, dtype=self.dtype)

        if self.fill.is_empty:
            # We have no fill value (either because the user explicitly
            # disabled it or because the default behaviour was used and our
            # elements strategy does not produce reusable values), so we must
            # generate a fully dense array with a freshly drawn value for each
            # entry.
            if self.unique:
                seen = set()
                elements = cu.many(
                    data,
                    min_size=self.array_size, max_size=self.array_size,
                    average_size=self.array_size
                )
                i = 0
                while elements.more():
                    # We assign first because this means we check for
                    # uniqueness after numpy has converted it to the relevant
                    # type for us. Because we don't increment the counter on
                    # a duplicate we will overwrite it on the next draw.
                    result[i] = data.draw(self.element_strategy)
                    if result[i] not in seen:
                        seen.add(result[i])
                        i += 1
                    else:
                        elements.reject()
            else:
                for i in hrange(len(result)):
                    result[i] = data.draw(self.element_strategy)
        else:
            # We draw numpy arrays as "sparse with an offset". We draw a
            # collection of index assignments within the array and assign
            # fresh values from our elements strategy to those indices. If at
            # the end we have not assigned every element then we draw a single
            # value from our fill strategy and use that to populate the
            # remaining positions with that strategy.

            elements = cu.many(
                data,
                min_size=0, max_size=self.array_size,
                # sqrt isn't chosen for any particularly principled reason. It
                # just grows reasonably quickly but sublinearly, and for small
                # arrays it represents a decent fraction of the array size.
                average_size=math.sqrt(self.array_size),
            )

            needs_fill = np.full(self.array_size, True)
            seen = set()

            while elements.more():
                i = cu.integer_range(data, 0, self.array_size - 1)
                if not needs_fill[i]:
                    elements.reject()
                    continue
                result[i] = data.draw(self.element_strategy)
                if self.unique:
                    if result[i] in seen:
                        elements.reject()
                        continue
                    else:
                        seen.add(result[i])
                needs_fill[i] = False
            if needs_fill.any():
                # We didn't fill all of the indices in the early loop, so we
                # put a fill value into the rest.

                # We have to do this hilarious little song and dance to work
                # around numpy's special handling of iterable values. If the
                # value here were e.g. a tuple then neither array creation
                # nor putmask would do the right thing. But by creating an
                # array of size one and then assigning the fill value as a
                # single element, we both get an array with the right value in
                # it and putmask will do the right thing by repeating the
                # values of the array across the mask.
                one_element = np.zeros(shape=1, dtype=self.dtype)
                one_element[0] = data.draw(self.fill)
                fill_value = one_element[0]
                if self.unique:
                    try:
                        is_nan = np.isnan(fill_value)
                    except TypeError:
                        is_nan = False

                    if not is_nan:
                        raise InvalidArgument(
                            'Cannot fill unique array with non-NaN '
                            'value %r' % (fill_value,))

                np.putmask(result, needs_fill, one_element)

        return result.reshape(self.shape)


@check_function
def fill_for(elements, unique, fill, name=''):
    if fill is None:
        if unique or not elements.has_reusable_values:
            fill = st.nothing()
        else:
            fill = elements
    else:
        st.check_strategy(fill, '%s.fill' % (name,) if name else 'fill')
    return fill


@st.composite
def arrays(
    draw, dtype, shape, elements=None, fill=None, unique=False
):
    """Returns a strategy for generating :class:`numpy's
    ndarrays<numpy.ndarray>`.

    * ``dtype`` may be any valid input to :class:`numpy.dtype <numpy.dtype>`
      (this includes ``dtype`` objects), or a strategy that generates such
      values.
    * ``shape`` may be an integer >= 0, a tuple of length >= 0 of such
      integers, or a strategy that generates such values.
    * ``elements`` is a strategy for generating values to put in the array.
      If it is None a suitable value will be inferred based on the dtype,
      which may give any legal value (including eg ``NaN`` for floats).
      If you have more specific requirements, you should supply your own
      elements strategy.
    * ``fill`` is a strategy that may be used to generate a single background
      value for the array. If None, a suitable default will be inferred
      based on the other arguments. If set to
      :func:`st.nothing() <hypothesis.strategies.nothing>` then filling
      behaviour will be disabled entirely and every element will be generated
      independently.
    * ``unique`` specifies if the elements of the array should all be
      distinct from one another. Note that in this case multiple NaN values
      may still be allowed. If fill is also set, the only valid values for
      it to return are NaN values (anything for which :func:`numpy.isnan`
      returns True. So e.g. for complex numbers (nan+1j) is also a valid fill).
      Note that if unique is set to True the generated values must be hashable.

    Arrays of specified ``dtype`` and ``shape`` are generated for example
    like this:

    .. code-block:: pycon

      >>> import numpy as np
      >>> arrays(np.int8, (2, 3)).example()
      array([[-8,  6,  3],
             [-6,  4,  6]], dtype=int8)

    - See :doc:`What you can generate and how <data>`.

    .. code-block:: pycon

      >>> import numpy as np
      >>> from hypothesis.strategies import floats
      >>> arrays(np.float, 3, elements=floats(0, 1)).example()
      array([ 0.88974794,  0.77387938,  0.1977879 ])

    Array values are generated in two parts:

    1. Some subset of the coordinates of the array are populated with a value
       drawn from the elements strategy (or its inferred form).
    2. If any coordinates were not assigned in the previous step, a single
       value is drawn from the fill strategy and is assigned to all remaining
       places.

    You can set fill to :func:`~hypothesis.strategies.nothing` if you want to
    disable this behaviour and draw a value for every element.

    If fill is set to None then it will attempt to infer the correct behaviour
    automatically: If unique is True, no filling will occur by default.
    Otherwise, if it looks safe to reuse the values of elements across
    multiple coordinates (this will be the case for any inferred strategy, and
    for most of the builtins, but is not the case for mutable values or
    strategies built with flatmap, map, composite, etc) then it will use the
    elements strategy as the fill, else it will default to having no fill.

    Having a fill helps Hypothesis craft high quality examples, but its
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
    fill = fill_for(
        elements=elements, unique=unique, fill=fill
    )
    return draw(ArrayStrategy(elements, shape, dtype, fill, unique))


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

    endianness and sizes are treated as for
    :func:`unsigned_integer_dtypes`.
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
    """Return a strategy for complex-number dtypes.

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
    subtype_strategy), or several such values drawn from
    :func:`array_dtypes` with ``allow_subarrays=True``. Subdtypes in an
    array dtype may be nested to any depth, subject to the max_leaves
    argument.
    """
    return st.recursive(subtype_strategy,
                        lambda x: array_dtypes(x, allow_subarrays=True),
                        max_leaves).filter(
        lambda d: max_itemsize is None or d.itemsize <= max_itemsize)
