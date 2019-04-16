# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

import math

import numpy as np

import hypothesis._strategies as st
import hypothesis.internal.conjecture.utils as cu
from hypothesis import Verbosity
from hypothesis._settings import note_deprecation
from hypothesis.errors import InvalidArgument
from hypothesis.internal.compat import hrange, integer_types, text_type
from hypothesis.internal.coverage import check_function
from hypothesis.internal.reflection import proxies
from hypothesis.internal.validation import check_type, check_valid_interval
from hypothesis.reporting import current_verbosity
from hypothesis.searchstrategy import SearchStrategy

if False:
    from typing import Any, Union, Sequence, Tuple, Optional  # noqa
    from hypothesis.searchstrategy.strategies import T  # noqa

TIME_RESOLUTIONS = tuple("Y  M  D  h  m  s  ms  us  ns  ps  fs  as".split())


@st.defines_strategy_with_reusable_values
def from_dtype(dtype):
    # type: (np.dtype) -> st.SearchStrategy[Any]
    """Creates a strategy which can generate any value of the given dtype."""
    check_type(np.dtype, dtype, "dtype")
    # Compound datatypes, eg 'f4,f4,f4'
    if dtype.names is not None:
        # mapping np.void.type over a strategy is nonsense, so return now.
        return st.tuples(*[from_dtype(dtype.fields[name][0]) for name in dtype.names])

    # Subarray datatypes, eg '(2, 3)i4'
    if dtype.subdtype is not None:
        subtype, shape = dtype.subdtype
        return arrays(subtype, shape)

    # Scalar datatypes
    if dtype.kind == u"b":
        result = st.booleans()  # type: SearchStrategy[Any]
    elif dtype.kind == u"f":
        if dtype.itemsize == 2:
            result = st.floats(width=16)
        elif dtype.itemsize == 4:
            result = st.floats(width=32)
        else:
            result = st.floats()
    elif dtype.kind == u"c":
        if dtype.itemsize == 8:
            float32 = st.floats(width=32)
            result = st.builds(complex, float32, float32)
        else:
            result = st.complex_numbers()
    elif dtype.kind in (u"S", u"a"):
        # Numpy strings are null-terminated; only allow round-trippable values.
        # `itemsize == 0` means 'fixed length determined at array creation'
        result = st.binary(max_size=dtype.itemsize or None).filter(
            lambda b: b[-1:] != b"\0"
        )
    elif dtype.kind == u"u":
        result = st.integers(min_value=0, max_value=2 ** (8 * dtype.itemsize) - 1)
    elif dtype.kind == u"i":
        overflow = 2 ** (8 * dtype.itemsize - 1)
        result = st.integers(min_value=-overflow, max_value=overflow - 1)
    elif dtype.kind == u"U":
        # Encoded in UTF-32 (four bytes/codepoint) and null-terminated
        result = st.text(max_size=(dtype.itemsize or 0) // 4 or None).filter(
            lambda b: b[-1:] != u"\0"
        )
    elif dtype.kind in (u"m", u"M"):
        if "[" in dtype.str:
            res = st.just(dtype.str.split("[")[-1][:-1])
        else:
            res = st.sampled_from(TIME_RESOLUTIONS)
        result = st.builds(dtype.type, st.integers(-2 ** 63, 2 ** 63 - 1), res)
    else:
        raise InvalidArgument(u"No strategy inference for {}".format(dtype))
    return result.map(dtype.type)


@check_function
def check_argument(condition, fail_message, *f_args, **f_kwargs):
    if not condition:
        raise InvalidArgument(fail_message.format(*f_args, **f_kwargs))


@check_function
def order_check(name, floor, small, large):
    check_argument(
        floor <= small,
        u"min_{name} must be at least {} but was {}",
        floor,
        small,
        name=name,
    )
    check_argument(
        small <= large,
        u"min_{name}={} is larger than max_{name}={}",
        small,
        large,
        name=name,
    )


class ArrayStrategy(SearchStrategy):
    def __init__(self, element_strategy, shape, dtype, fill, unique):
        self.shape = tuple(shape)
        self.fill = fill
        self.array_size = int(np.prod(shape))
        self.dtype = dtype
        self.element_strategy = element_strategy
        self.unique = unique

        # Used by self.insert_element to check that the value can be stored
        # in the array without e.g. overflowing.  See issues #1385 and #1591.
        if dtype.kind in (u"i", u"u"):
            self.check_cast = lambda x: np.can_cast(x, self.dtype, "safe")
        elif dtype.kind == u"f" and dtype.itemsize == 2:
            max_f2 = (2.0 - 2 ** -10) * 2 ** 15
            self.check_cast = lambda x: (not np.isfinite(x)) or (-max_f2 <= x <= max_f2)
        elif dtype.kind == u"f" and dtype.itemsize == 4:
            max_f4 = (2.0 - 2 ** -23) * 2 ** 127
            self.check_cast = lambda x: (not np.isfinite(x)) or (-max_f4 <= x <= max_f4)
        elif dtype.kind == u"c" and dtype.itemsize == 8:
            max_f4 = (2.0 - 2 ** -23) * 2 ** 127
            self.check_cast = lambda x: (not np.isfinite(x)) or (
                -max_f4 <= x.real <= max_f4 and -max_f4 <= x.imag <= max_f4
            )
        elif dtype.kind == u"U":
            length = dtype.itemsize // 4
            self.check_cast = lambda x: len(x) <= length and u"\0" not in x[length:]
        elif dtype.kind in (u"S", u"a"):
            self.check_cast = (
                lambda x: len(x) <= dtype.itemsize and b"\0" not in x[dtype.itemsize :]
            )
        else:
            self.check_cast = lambda x: True

    def set_element(self, data, result, idx, strategy=None):
        strategy = strategy or self.element_strategy
        val = data.draw(strategy)
        result[idx] = val
        if self._report_overflow and not self.check_cast(val):
            note_deprecation(
                "Generated array element %r from %r cannot be represented as "
                "dtype %r - instead it becomes %r .  Consider using a more "
                "precise strategy, as this will be an error in a future "
                "version." % (val, strategy, self.dtype, result[idx]),
                since="2018-10-25",
            )
            # Because the message includes the value of the generated element,
            # it would be easy to spam users with thousands of warnings.
            # We therefore only warn once per draw, unless in verbose mode.
            self._report_overflow = current_verbosity() >= Verbosity.verbose

    def do_draw(self, data):
        if 0 in self.shape:
            return np.zeros(dtype=self.dtype, shape=self.shape)

        # Reset this flag for each test case to emit warnings from set_element
        self._report_overflow = True

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
                    min_size=self.array_size,
                    max_size=self.array_size,
                    average_size=self.array_size,
                )
                i = 0
                while elements.more():
                    # We assign first because this means we check for
                    # uniqueness after numpy has converted it to the relevant
                    # type for us. Because we don't increment the counter on
                    # a duplicate we will overwrite it on the next draw.
                    self.set_element(data, result, i)
                    if result[i] not in seen:
                        seen.add(result[i])
                        i += 1
                    else:
                        elements.reject()
            else:
                for i in hrange(len(result)):
                    self.set_element(data, result, i)
        else:
            # We draw numpy arrays as "sparse with an offset". We draw a
            # collection of index assignments within the array and assign
            # fresh values from our elements strategy to those indices. If at
            # the end we have not assigned every element then we draw a single
            # value from our fill strategy and use that to populate the
            # remaining positions with that strategy.

            elements = cu.many(
                data,
                min_size=0,
                max_size=self.array_size,
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
                self.set_element(data, result, i)
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
                self.set_element(data, one_element, 0, self.fill)
                fill_value = one_element[0]
                if self.unique:
                    try:
                        is_nan = np.isnan(fill_value)
                    except TypeError:
                        is_nan = False

                    if not is_nan:
                        raise InvalidArgument(
                            "Cannot fill unique array with non-NaN "
                            "value %r" % (fill_value,)
                        )

                np.putmask(result, needs_fill, one_element)

        return result.reshape(self.shape)


@check_function
def fill_for(elements, unique, fill, name=""):
    if fill is None:
        if unique or not elements.has_reusable_values:
            fill = st.nothing()
        else:
            fill = elements
    else:
        st.check_strategy(fill, "%s.fill" % (name,) if name else "fill")
    return fill


@st.defines_strategy
def arrays(
    dtype,  # type: Any
    shape,  # type: Union[int, Sequence[int], st.SearchStrategy[Sequence[int]]]
    elements=None,  # type: st.SearchStrategy[Any]
    fill=None,  # type: st.SearchStrategy[Any]
    unique=False,  # type: bool
):
    # type: (...) -> st.SearchStrategy[np.ndarray]
    r"""Returns a strategy for generating :class:`numpy:numpy.ndarray`\ s.

    * ``dtype`` may be any valid input to :class:`~numpy:numpy.dtype`
      (this includes :class:`~numpy:numpy.dtype` objects), or a strategy that
      generates such values.
    * ``shape`` may be an integer >= 0, a tuple of such integers, or a
      strategy that generates such values.
    * ``elements`` is a strategy for generating values to put in the array.
      If it is None a suitable value will be inferred based on the dtype,
      which may give any legal value (including eg ``NaN`` for floats).
      If you have more specific requirements, you should supply your own
      elements strategy.
    * ``fill`` is a strategy that may be used to generate a single background
      value for the array. If None, a suitable default will be inferred
      based on the other arguments. If set to
      :func:`~hypothesis.strategies.nothing` then filling
      behaviour will be disabled entirely and every element will be generated
      independently.
    * ``unique`` specifies if the elements of the array should all be
      distinct from one another. Note that in this case multiple NaN values
      may still be allowed. If fill is also set, the only valid values for
      it to return are NaN values (anything for which :obj:`numpy:numpy.isnan`
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
    # We support passing strategies as arguments for convenience, or at least
    # for legacy reasons, but don't want to pay the perf cost of a composite
    # strategy (i.e. repeated argument handling and validation) when it's not
    # needed.  So we get the best of both worlds by recursing with flatmap,
    # but only when it's actually needed.
    if isinstance(dtype, SearchStrategy):
        return dtype.flatmap(
            lambda d: arrays(d, shape, elements=elements, fill=fill, unique=unique)
        )
    if isinstance(shape, SearchStrategy):
        return shape.flatmap(
            lambda s: arrays(dtype, s, elements=elements, fill=fill, unique=unique)
        )
    # From here on, we're only dealing with values and it's relatively simple.
    dtype = np.dtype(dtype)
    if elements is None:
        elements = from_dtype(dtype)
    if isinstance(shape, integer_types):
        shape = (shape,)
    shape = tuple(shape)
    check_argument(
        all(isinstance(s, integer_types) for s in shape),
        "Array shape must be integer in each dimension, provided shape was {}",
        shape,
    )
    fill = fill_for(elements=elements, unique=unique, fill=fill)
    return ArrayStrategy(elements, shape, dtype, fill, unique)


@st.defines_strategy
def array_shapes(min_dims=1, max_dims=3, min_side=1, max_side=10):
    # type: (int, int, int, int) -> st.SearchStrategy[Tuple[int, ...]]
    """Return a strategy for array shapes (tuples of int >= 1)."""
    order_check("dims", 0, min_dims, max_dims)
    order_check("side", 0, min_side, max_side)
    return st.lists(
        st.integers(min_side, max_side), min_size=min_dims, max_size=max_dims
    ).map(tuple)


@st.defines_strategy
def scalar_dtypes():
    # type: () -> st.SearchStrategy[np.dtype]
    """Return a strategy that can return any non-flexible scalar dtype."""
    return st.one_of(
        boolean_dtypes(),
        integer_dtypes(),
        unsigned_integer_dtypes(),
        floating_dtypes(),
        complex_number_dtypes(),
        datetime64_dtypes(),
        timedelta64_dtypes(),
    )


def defines_dtype_strategy(strat):
    # type: (T) -> T
    @st.defines_strategy
    @proxies(strat)
    def inner(*args, **kwargs):
        strategy = strat(*args, **kwargs)

        def convert_to_dtype(x):
            """Helper to debug issue #1798."""
            try:
                return np.dtype(x)
            except ValueError:
                print(
                    "Got invalid dtype value=%r from strategy=%r, function=%r"
                    % (x, strategy, strat)
                )
                raise

        return strategy.map(convert_to_dtype)

    return inner


@defines_dtype_strategy
def boolean_dtypes():
    # type: () -> st.SearchStrategy[np.dtype]
    return st.just("?")


def dtype_factory(kind, sizes, valid_sizes, endianness):
    # Utility function, shared logic for most integer and string types
    valid_endian = ("?", "<", "=", ">")
    check_argument(
        endianness in valid_endian,
        u"Unknown endianness: was {}, must be in {}",
        endianness,
        valid_endian,
    )
    if valid_sizes is not None:
        if isinstance(sizes, int):
            sizes = (sizes,)
        check_argument(sizes, "Dtype must have at least one possible size.")
        check_argument(
            all(s in valid_sizes for s in sizes),
            u"Invalid sizes: was {} must be an item or sequence " u"in {}",
            sizes,
            valid_sizes,
        )
        if all(isinstance(s, int) for s in sizes):
            sizes = sorted(set(s // 8 for s in sizes))
    strat = st.sampled_from(sizes)
    if "{}" not in kind:
        kind += "{}"
    if endianness == "?":
        return strat.map(("<" + kind).format) | strat.map((">" + kind).format)
    return strat.map((endianness + kind).format)


@defines_dtype_strategy
def unsigned_integer_dtypes(endianness="?", sizes=(8, 16, 32, 64)):
    # type: (str, Sequence[int]) -> st.SearchStrategy[np.dtype]
    """Return a strategy for unsigned integer dtypes.

    endianness may be ``<`` for little-endian, ``>`` for big-endian,
    ``=`` for native byte order, or ``?`` to allow either byte order.
    This argument only applies to dtypes of more than one byte.

    sizes must be a collection of integer sizes in bits.  The default
    (8, 16, 32, 64) covers the full range of sizes.
    """
    return dtype_factory("u", sizes, (8, 16, 32, 64), endianness)


@defines_dtype_strategy
def integer_dtypes(endianness="?", sizes=(8, 16, 32, 64)):
    # type: (str, Sequence[int]) -> st.SearchStrategy[np.dtype]
    """Return a strategy for signed integer dtypes.

    endianness and sizes are treated as for
    :func:`unsigned_integer_dtypes`.
    """
    return dtype_factory("i", sizes, (8, 16, 32, 64), endianness)


@defines_dtype_strategy
def floating_dtypes(endianness="?", sizes=(16, 32, 64)):
    # type: (str, Sequence[int]) -> st.SearchStrategy[np.dtype]
    """Return a strategy for floating-point dtypes.

    sizes is the size in bits of floating-point number.  Some machines support
    96- or 128-bit floats, but these are not generated by default.

    Larger floats (96 and 128 bit real parts) are not supported on all
    platforms and therefore disabled by default.  To generate these dtypes,
    include these values in the sizes argument.
    """
    return dtype_factory("f", sizes, (16, 32, 64, 96, 128), endianness)


@defines_dtype_strategy
def complex_number_dtypes(endianness="?", sizes=(64, 128)):
    # type: (str, Sequence[int]) -> st.SearchStrategy[np.dtype]
    """Return a strategy for complex-number dtypes.

    sizes is the total size in bits of a complex number, which consists
    of two floats.  Complex halfs (a 16-bit real part) are not supported
    by numpy and will not be generated by this strategy.
    """
    return dtype_factory("c", sizes, (64, 128, 192, 256), endianness)


@check_function
def validate_time_slice(max_period, min_period):
    check_argument(
        max_period in TIME_RESOLUTIONS,
        u"max_period {} must be a valid resolution in {}",
        max_period,
        TIME_RESOLUTIONS,
    )
    check_argument(
        min_period in TIME_RESOLUTIONS,
        u"min_period {} must be a valid resolution in {}",
        min_period,
        TIME_RESOLUTIONS,
    )
    start = TIME_RESOLUTIONS.index(max_period)
    end = TIME_RESOLUTIONS.index(min_period) + 1
    check_argument(
        start < end,
        u"max_period {} must be earlier in sequence {} than " u"min_period {}",
        max_period,
        TIME_RESOLUTIONS,
        min_period,
    )
    return TIME_RESOLUTIONS[start:end]


@defines_dtype_strategy
def datetime64_dtypes(max_period="Y", min_period="ns", endianness="?"):
    # type: (str, str, str) -> st.SearchStrategy[np.dtype]
    """Return a strategy for datetime64 dtypes, with various precisions from
    year to attosecond."""
    return dtype_factory(
        "datetime64[{}]",
        validate_time_slice(max_period, min_period),
        TIME_RESOLUTIONS,
        endianness,
    )


@defines_dtype_strategy
def timedelta64_dtypes(max_period="Y", min_period="ns", endianness="?"):
    # type: (str, str, str) -> st.SearchStrategy[np.dtype]
    """Return a strategy for timedelta64 dtypes, with various precisions from
    year to attosecond."""
    return dtype_factory(
        "timedelta64[{}]",
        validate_time_slice(max_period, min_period),
        TIME_RESOLUTIONS,
        endianness,
    )


@defines_dtype_strategy
def byte_string_dtypes(endianness="?", min_len=0, max_len=16):
    # type: (str, int, int) -> st.SearchStrategy[np.dtype]
    """Return a strategy for generating bytestring dtypes, of various lengths
    and byteorder."""
    order_check("len", 0, min_len, max_len)
    return dtype_factory("S", list(range(min_len, max_len + 1)), None, endianness)


@defines_dtype_strategy
def unicode_string_dtypes(endianness="?", min_len=0, max_len=16):
    # type: (str, int, int) -> st.SearchStrategy[np.dtype]
    """Return a strategy for generating unicode string dtypes, of various
    lengths and byteorder."""
    order_check("len", 0, min_len, max_len)
    return dtype_factory("U", list(range(min_len, max_len + 1)), None, endianness)


@defines_dtype_strategy
def array_dtypes(
    subtype_strategy=scalar_dtypes(),  # type: st.SearchStrategy[np.dtype]
    min_size=1,  # type: int
    max_size=5,  # type: int
    allow_subarrays=False,  # type: bool
):
    # type: (...) -> st.SearchStrategy[np.dtype]
    """Return a strategy for generating array (compound) dtypes, with members
    drawn from the given subtype strategy."""
    order_check("size", 0, min_size, max_size)
    native_strings = st.text()  # type: SearchStrategy[Any]
    if text_type is not str:  # pragma: no cover
        native_strings = st.binary()
    elements = st.tuples(native_strings, subtype_strategy)
    if allow_subarrays:
        elements |= st.tuples(
            native_strings, subtype_strategy, array_shapes(max_dims=2, max_side=2)
        )
    return st.lists(
        elements=elements,
        min_size=min_size,
        max_size=max_size,
        unique_by=lambda d: d[0],
    )


@st.defines_strategy
def nested_dtypes(
    subtype_strategy=scalar_dtypes(),  # type: st.SearchStrategy[np.dtype]
    max_leaves=10,  # type: int
    max_itemsize=None,  # type: int
):
    # type: (...) -> st.SearchStrategy[np.dtype]
    """Return the most-general dtype strategy.

    Elements drawn from this strategy may be simple (from the
    subtype_strategy), or several such values drawn from
    :func:`array_dtypes` with ``allow_subarrays=True``. Subdtypes in an
    array dtype may be nested to any depth, subject to the max_leaves
    argument.
    """
    return st.recursive(
        subtype_strategy, lambda x: array_dtypes(x, allow_subarrays=True), max_leaves
    ).filter(lambda d: max_itemsize is None or d.itemsize <= max_itemsize)


@st.defines_strategy
def valid_tuple_axes(ndim, min_size=0, max_size=None):
    # type: (int, int, int) -> st.SearchStrategy[Tuple[int, ...]]
    """Return a strategy for generating permissible tuple-values for the
    ``axis`` argument for a numpy sequential function (e.g.
    :func:`numpy:numpy.sum`), given an array of the specified
    dimensionality.

    All tuples will have an length >= min_size and <= max_size. The default
    value for max_size is ``ndim``.

    Examples from this strategy shrink towards an empty tuple, which render
    most sequential functions as no-ops.

    The following are some examples drawn from this strategy.

    .. code-block:: pycon

        >>> [valid_tuple_axes(3).example() for i in range(4)]
        [(-3, 1), (0, 1, -1), (0, 2), (0, -2, 2)]

    ``valid_tuple_axes`` can be joined with other strategies to generate
    any type of valid axis object, i.e. integers, tuples, and ``None``:

    .. code-block:: pycon

        any_axis_strategy = none() | integers(-ndim, ndim - 1) | valid_tuple_axes(ndim)

    """
    if max_size is None:
        max_size = ndim

    check_type(integer_types, ndim, "ndim")
    check_type(integer_types, min_size, "min_size")
    check_type(integer_types, max_size, "max_size")
    order_check("size", 0, min_size, max_size)
    check_valid_interval(max_size, ndim, "max_size", "ndim")

    # shrink axis values from negative to positive
    axes = st.integers(0, max(0, 2 * ndim - 1)).map(
        lambda x: x if x < ndim else x - 2 * ndim
    )
    return st.lists(axes, min_size, max_size, unique_by=lambda x: x % ndim).map(tuple)


class BroadcastShapeStrategy(SearchStrategy):
    def __init__(self, shape, min_dims, max_dims, min_side, max_side):
        assert 0 <= min_side <= max_side
        assert 0 <= min_dims <= max_dims <= 32
        SearchStrategy.__init__(self)
        self.shape = shape
        self.side_strat = st.integers(min_side, max_side)
        self.min_dims = min_dims
        self.max_dims = max_dims
        self.min_side = min_side
        self.max_side = max_side

    def do_draw(self, data):
        elements = cu.many(
            data,
            min_size=self.min_dims,
            max_size=self.max_dims,
            average_size=min(
                max(self.min_dims * 2, self.min_dims + 5),
                0.5 * (self.min_dims + self.max_dims),
            ),
        )
        result = []
        reversed_shape = tuple(self.shape[::-1])
        while elements.more():
            if len(result) < len(self.shape):
                # Shrinks towards original shape
                if reversed_shape[len(result)] == 1:
                    if self.min_side <= 1 and not data.draw(st.booleans()):
                        side = 1
                    else:
                        side = data.draw(self.side_strat)
                elif self.max_side >= reversed_shape[len(result)] and (
                    not self.min_side <= 1 <= self.max_side or data.draw(st.booleans())
                ):
                    side = reversed_shape[len(result)]
                else:
                    side = 1
            else:
                side = data.draw(self.side_strat)
            result.append(side)
        assert self.min_dims <= len(result) <= self.max_dims
        assert all(self.min_side <= s <= self.max_side for s in result)
        return tuple(reversed(result))


@st.defines_strategy
def broadcastable_shapes(shape, min_dims=0, max_dims=None, min_side=1, max_side=None):
    # type: (Sequence[int], int, Optional[int], int, Optional[int]) -> st.SearchStrategy[Tuple[int, ...]]
    """Return a strategy for generating shapes that are broadcast-compatible
    with the provided shape.

    Examples from this strategy shrink towards a shape with length ``min_dims``.
    The size of an aligned dimension shrinks towards being a singleton. The
    size of an unaligned dimension shrink towards ``min_side``.

    * ``shape`` a tuple of integers
    * ``min_dims`` The smallest length that the generated shape can possess.
    * ``max_dims`` The largest length that the generated shape can possess.
      shape can possess. Cannot exceed 32. The default-value for ``max_dims``
      is ``2 + max(len(shape), min_dims)``.
    * ``min_side`` The smallest size that an unaligned dimension can possess.
    * ``max_side`` The largest size that an unaligned dimension can possess.
      The default value is 2 + 'size-of-largest-aligned-dimension'.

    The following are some examples drawn from this strategy.

    .. code-block:: pycon

        >>> [broadcastable_shapes(shape=(2, 3)).example() for i in range(5)]
        [(1, 3), (), (2, 3), (2, 1), (4, 1, 3), (3, )]

    """
    check_type(tuple, shape, "shape")
    strict_check = max_side is None or max_dims is None
    check_type(integer_types, min_side, "min_side")
    check_type(integer_types, min_dims, "min_dims")

    if max_dims is None:
        max_dims = max(len(shape), min_dims) + 2
    else:
        check_type(integer_types, max_dims, "max_dims")

    if max_side is None:
        max_side = max(tuple(shape[-max_dims:]) + (min_side,)) + 2
    else:
        check_type(integer_types, max_side, "max_side")

    order_check("dims", 0, min_dims, max_dims)
    order_check("side", 0, min_side, max_side)

    if 32 < max_dims:
        raise InvalidArgument("max_dims cannot exceed 32")

    dims, bnd_name = (max_dims, "max_dims") if strict_check else (min_dims, "min_dims")

    # check for unsatisfiable min_side
    if not all(min_side <= s for s in shape[::-1][:dims] if s != 1):
        raise InvalidArgument(
            "Given shape=%r, there are no broadcast-compatible "
            "shapes that satisfy: %s=%s and min_side=%s"
            % (shape, bnd_name, dims, min_side)
        )

    # check for unsatisfiable [min_side, max_side]
    if not (
        min_side <= 1 <= max_side or all(s <= max_side for s in shape[::-1][:dims])
    ):
        raise InvalidArgument(
            "Given shape=%r, there are no broadcast-compatible shapes "
            "that satisfy: %s=%s and [min_side=%s, max_side=%s]"
            % (shape, bnd_name, dims, min_side, max_side)
        )

    if not strict_check:
        # reduce max_dims to exclude unsatisfiable dimensions
        for n, s in zip(range(max_dims), reversed(shape)):
            if s < min_side and s != 1:
                max_dims = n
                break
            elif not (min_side <= 1 <= max_side or s <= max_side):
                max_dims = n
                break

    return BroadcastShapeStrategy(
        shape,
        min_dims=min_dims,
        max_dims=max_dims,
        min_side=min_side,
        max_side=max_side,
    )
