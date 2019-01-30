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

# This module uses the numpy parser of the Generalized Universal Function API
# signatures `_parse_gufunc_signature`, which is only available in
# numpy>=1.12.0 and therefore requires a bump in the requirements for
# hypothesis.
from __future__ import absolute_import, division, print_function

import string
from collections import defaultdict

import numpy as np
import numpy.lib.function_base as npfb

from hypothesis.errors import InvalidArgument
from hypothesis.extra.numpy import arrays, order_check
from hypothesis.internal.compat import integer_types
from hypothesis.internal.validation import check_type, check_valid_bound
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.strategies import (
    builds,
    composite,
    fixed_dictionaries,
    integers,
    just,
    tuples,
)

__all__ = ["gufunc_args", "gufunc_arg_shapes"]

# Should not ever need to broadcast beyond this, but should be able to set it
# as high as 32 before breaking assumptions in numpy.
GLOBAL_DIMS_MAX = 12


# Key used in min_side and max_side to indicate min/max on broadcasted dims,
# building sentinel class so we have clean __repr__.
class _BcastDimType(object):
    def __repr__(self):
        return "BCAST_DIM"


BCAST_DIM = _BcastDimType()

# Value used in default dict for max side if variable not specified
DEFAULT_MAX_SIDE = 5

# This uses "private" function of numpy, but it does the job. It throws a
# pretty readable exception for invalid input, we don't need to add anything.
parse_gufunc_signature = npfb._parse_gufunc_signature


def _weird_digits(ss):
    """In Python 3, some weird unicode characters pass `isdigit` but are not
    0-9 characters. This function detects those cases.
    """
    weird = set(cc for cc in ss if cc.isdigit() and (cc not in string.digits))
    return weird


def _check_set_like(arg, name=""):
    """Validate input can be searched like a `set`."""
    try:
        0 in arg
    except TypeError:
        raise InvalidArgument(
            "Expected set-like but got %s=%r (type=%s)"
            % (name, arg, type(arg).__name__)
        )


def _check_valid_size_interval(min_size, max_size, name, floor=0):
    """Check valid for integers strategy and array shapes."""
    # same checks as done in integers
    check_valid_bound(min_size, name)
    check_valid_bound(max_size, name)
    order_check(name, floor, min_size, max_size)  # ensure non-none & above 0


def _order_check_min_max(min_dict, max_dict):
    """Check min and max dict compatible with integers and array shapes."""
    _check_valid_size_interval(
        min_dict.default_factory(), max_dict.default_factory(), "side default"
    )
    for kk in set(min_dict.keys()) | set(max_dict.keys()):
        _check_valid_size_interval(min_dict[kk], max_dict[kk], "side %s" % kk)


def _int_or_dict(x, default_val):
    """Pre-process cases where argument `x` can be `int`, `dict`, or
    `defaultdict`. In all cases, build a `defaultdict` and return it.
    """
    # case 1: x already defaultdict, leave it be, pass thru
    if isinstance(x, defaultdict):
        return x

    check_type(integer_types, default_val, "default value")
    try:
        # case 2: x is or can be converted to dict
        D = defaultdict(lambda: default_val, x)
    except Exception:
        # case 3: x is int => make a const dict
        check_type(integer_types, x, "constant value")
        D = defaultdict(lambda: x)
    # case 4: if can't be converted to dict or int, then exception raised
    return D


@composite
def _tuple_of_arrays(draw, shapes, dtype, elements, unique=False):
    """Strategy to generate a tuple of ndarrays with specified shapes.

    Parameters
    ----------
    shapes : list of tuples of int
        List of tuples where each tuple is the shape of an argument. A
        `SearchStrategy` for list of tuples is also supported.
    dtype : list-like of dtype
        List of numpy `dtype` for each argument. These can be either strings
        (``'int64'``), type (``np.int64``), or numpy `dtype`
        (``np.dtype('int64')``). Built in Python types (`int`, `float`, etc)
        also work. A single `dtype` can be supplied for all arguments.
    elements : list-like of strategy
        Strategies to fill in array elements on a per argument basis. One can
        also specify a single strategy
        (e.g., :func:`~hypothesis.strategies.floats`)
        and have it applied to all arguments.
    unique : list-like of bool
        Boolean flag to specify if all elements in an array must be unique.
        One can also specify a single boolean to apply it to all arguments.

    Returns
    -------
    res : tuple of ndarrays
        Resulting ndarrays with shape of `shapes` and elements from `elements`.

    """
    if isinstance(shapes, SearchStrategy):
        shapes = draw(shapes)
    n = len(shapes)

    # Need this since broadcast_to does not like vars of type type
    if isinstance(dtype, type):
        dtype = [dtype]
    dtype = np.broadcast_to(dtype, (n,))

    elements = np.broadcast_to(elements, (n,))
    unique = np.broadcast_to(unique, (n,))

    # This could somewhat easily be done using builds and avoid need for
    # composite if shape is always given and not strategy. Otherwise, we need
    # to chain strategies and probably not worth the effort.
    res = tuple(
        draw(arrays(dd, ss, elements=ee, unique=uu))
        for dd, ss, ee, uu in zip(dtype, shapes, elements, unique)
    )
    return res


def _signature_map(map_dict, parsed_sig):
    """Map values found in parsed gufunc signature.

    Parameters
    ----------
    map_dict : dict of str to int
        Mapping from `str` dimension names to `int`. All strings in
        `parsed_sig` must have entries in `map_dict`.
    parsed_sig : list-like of tuples of str
        gufunc signature that has already been parsed, e.g., using
        `parse_gufunc_signature`.

    Returns
    -------
    shapes : list of tuples of int
        list of tuples where each tuple is the shape of an argument.

    """
    shapes = [tuple(map_dict[k] for k in arg) for arg in parsed_sig]
    return shapes


def _gufunc_arg_shapes(parsed_sig, min_side, max_side):
    """Strategy to generate array shapes for arguments to a function consistent
    with its signature.

    Parameters
    ----------
    parsed_sig : list-like of tuples of str
        gufunc signature that has already been parsed, e.g., using
        `parse_gufunc_signature`.
    min_side : defaultdict of str to int
        Minimum size of any of the dimensions in `parsed_sig`.
    max_side : defaultdict of str to int
        Maximum size of any of the dimensions in `parsed_sig`.

    Returns
    -------
    shapes : list of tuples of int
        list of tuples where each tuple is the shape of an argument.

    """
    assert min_side.default_factory() <= max_side.default_factory()
    min_max_ok = all(
        min_side[kk] <= max_side[kk]
        for kk in set(min_side.keys()) | set(max_side.keys())
    )
    assert min_max_ok

    # Get all dimension names in signature, including numeric constants
    all_dimensions = set([k for arg in parsed_sig for k in arg])

    # Assume we have already checked for weird unicode characters that mess up
    # isdigit in validation of signature.
    dim_map_st = {
        k: (
            just(int(k))
            if k.isdigit()
            else integers(min_value=min_side[k], max_value=max_side[k])
        )
        for k in all_dimensions
    }

    # Build strategy that draws ints for dimensions and subs them in
    return builds(
        _signature_map,
        map_dict=fixed_dictionaries(dim_map_st),
        parsed_sig=just(parsed_sig),
    )


def _append_bcast_dims(core_dims, b_dims, set_to_1, n_extra_per_arg):
    """Add extra broadcast dimensions to core dimensions of array shapes.

    Parameters
    ----------
    core_dims : list of tuples of int
        list of tuples where each tuple is the core shape of an argument. It
        has length `n_args`.
    b_dims : ndarray of shape (max_dims_extra,)
        Must be of `int` dtype and >= 0. Extra dimensions to pre-pend for
        roadcasting.
    set_to_1 : ndarray of shape (n_args, max_dims_extra)
        Must be of `bool` dtype. Which extra dimensions get set to 1 for
        broadcasting.
    n_extra_per_arg : like-like of shape (n_args,)
        Elements must be of int type. Must be in [0, max_dims_extra], how many
        extra dimensions to pre-pend to each argument.

    Returns
    -------
    shapes : list of tuples of int
        list of tuples where each tuple is the shape of an argument. Extra
        dimensions for broadcasting will be present in the shapes. It has
        length `n_args`.

    """
    # Build 2D array with extra dimensions
    # e.g., extra_dims = [[2 5], [2 5]]
    extra_dims = np.tile(b_dims, (len(core_dims), 1))
    # e.g., extra_dims = [[1 5], [2 5]]
    extra_dims[set_to_1] = 1  # This may be outside [min_side, max_side]

    # Get full dimensions (core+extra), will chop some on left randomly
    # e.g., shapes = [(5, 1, 3), (2, 5, 3, 1)]
    # We use pp[len(pp) - nn:] instead of pp[-nn:] since that doesn't handle
    # corner case with nn=0 correctly (seems like an oversight of py slicing).
    # Call tolist() before tuple to ensure native int type.
    shapes = [
        tuple(pp[len(pp) - nn :].tolist()) + ss
        for ss, pp, nn in zip(core_dims, extra_dims, n_extra_per_arg)
    ]
    return shapes


def gufunc_arg_shapes(signature, excluded=(), min_side=0, max_side=5, max_dims_extra=0):
    """Strategy to generate the shape of ndarrays for arguments to a function
    consistent with its signature with extra dimensions to test broadcasting.

    Parameters
    ----------
    signature : str
        Signature for shapes to be compatible with. Expects string in format
        of numpy generalized universal function signature, e.g.,
        `'(m,n),(n)->(m)'` for vectorized matrix-vector multiplication.
    excluded : set(int)
        Set-like of integers representing the positional for which the function
        will not be vectorized. Uses same format as :obj:`numpy.vectorize`.
    min_side : int or dict
        Minimum size of any side of the arrays. It is good to test the corner
        cases of 0 or 1 sized dimensions when applicable, but if not, a min
        size can be supplied here. Minimums can be provided on a per-dimension
        basis using a dict, e.g. ``min_side={'n': 2}``. One can use, e.g.,
        ``min_side={hypothesis.extra.gufunc.BCAST_DIM: 2}`` to limit the size
        of the broadcasted dimensions.
    max_side : int or dict
        Maximum size of any side of the arrays. This can usually be kept small
        and still find most corner cases in testing. Dictionaries can be
        supplied as with `min_side`.
    max_dims_extra : int
        Maximum number of extra dimensions that can be appended on left of
        arrays for broadcasting. This should be kept small as the memory used
        grows exponentially with extra dimensions. By default, no extra
        dimensions are added.

    Returns
    -------
    shapes : list(tuple(int))
        list of tuples where each tuple is the shape of an argument. Extra
        dimensions for broadcasting will be present in the shapes.

    Examples
    --------
    .. code-block:: pycon

      >>> from hypothesis.extra.gufunc import BCAST_DIM
      >>> gufunc_arg_shapes('(m,n),(n)->(m)',
                            min_side={'m': 1, 'n': 2}, max_side=3).example()
      [(2, 3), (3,)]
      >>> gufunc_arg_shapes('(m,n),(n)->(m)', max_side=9,
                            min_side={'m': 1, 'n': 2, BCAST_DIM: 5},
                            max_dims_extra=3).example()
      [(6, 6, 7), (6, 7)]
      >>> gufunc_arg_shapes('(m,n),(n)->(m)', excluded=(0,),
                            max_side=20, max_dims_extra=3).example()
      [(11, 13), (1, 1, 1, 13)]

    """
    _check_set_like(excluded, name="excluded")
    min_side = _int_or_dict(min_side, 0)
    max_side = _int_or_dict(max_side, DEFAULT_MAX_SIDE)
    _order_check_min_max(min_side, max_side)
    check_type(integer_types, max_dims_extra, "extra dims")
    order_check("extra dims", 0, max_dims_extra, GLOBAL_DIMS_MAX)

    # Validate that the signature contains digits we can parse
    weird_sig_digits = _weird_digits(signature)
    if len(weird_sig_digits) > 0:
        raise InvalidArgument(
            "signature %s contains invalid digits: %s"
            % (signature, "".join(weird_sig_digits))
        )

    # Parse out the signature: e.g., parses to [('n', 'm'), ('m', 'p')]
    parsed_sig, _ = parse_gufunc_signature(signature)

    # Get core shapes before broadcasted dimensions
    shapes_st = _gufunc_arg_shapes(parsed_sig, min_side=min_side, max_side=max_side)

    # Skip this broadcasting craziness if we don't want extra dims:
    if max_dims_extra == 0:
        return shapes_st

    # We could use tuples instead without creating type ambiguity since
    # max_dims_extra > 0 and avoid calling arrays, but prob ok like this.
    bcast_dim_st = integers(
        min_value=min_side[BCAST_DIM], max_value=max_side[BCAST_DIM]
    )
    extra_dims_st = arrays(np.intp, (max_dims_extra,), elements=bcast_dim_st)

    set_to_1_st = arrays(np.bool_, (len(parsed_sig), max_dims_extra))

    # np.clip will convert to np int but we don't really care.
    max_extra_per_arg = [
        0 if nn in excluded else np.clip(GLOBAL_DIMS_MAX - len(ss), 0, max_dims_extra)
        for nn, ss in enumerate(parsed_sig)
    ]
    extra_per_arg_st = tuples(
        *[integers(min_value=0, max_value=mm) for mm in max_extra_per_arg]
    )

    return builds(
        _append_bcast_dims, shapes_st, extra_dims_st, set_to_1_st, extra_per_arg_st
    )


def gufunc_args(
    signature,
    dtype,
    elements,
    unique=False,
    excluded=(),
    min_side=0,
    max_side=5,
    max_dims_extra=0,
):
    """Strategy to generate a tuple of ndarrays for arguments to a function
    consistent with its signature with extra dimensions to test broadcasting.

    Parameters
    ----------
    signature : str
        Signature for shapes to be compatible with. Expects string in format
        of numpy generalized universal function signature, e.g.,
        `'(m,n),(n)->(m)'` for vectorized matrix-vector multiplication.
    dtype : list(:class:`numpy:numpy.dtype`)
        List of numpy `dtype` for each argument. These can be either strings
        (``'int64'``), type (``np.int64``), or numpy `dtype`
        (``np.dtype('int64')``). Built in Python types (`int`, `float`, etc)
        also work. A single `dtype` can be supplied for all arguments.
    elements : list
        List of strategies to fill in array elements on a per argument basis.
        One can also specify a single strategy
        (e.g., :func:`~hypothesis.strategies.floats`)
        and have it applied to all arguments.
    unique : list(bool)
        Boolean flag to specify if all elements in an array must be unique.
        One can also specify a single boolean to apply it to all arguments.
    excluded : set(int)
        Set of integers representing the positional for which the function will
        not be vectorized. Uses same format as :obj:`numpy.vectorize`.
    min_side : int or dict
        Minimum size of any side of the arrays. It is good to test the corner
        cases of 0 or 1 sized dimensions when applicable, but if not, a min
        size can be supplied here. Minimums can be provided on a per-dimension
        basis using a dict, e.g. ``min_side={'n': 2}``. One can use, e.g.,
        ``min_side={hypothesis.extra.gufunc.BCAST_DIM: 2}`` to limit the size
        of the broadcasted dimensions.
    max_side : int or dict
        Maximum size of any side of the arrays. This can usually be kept small
        and still find most corner cases in testing. Dictionaries can be
        supplied as with `min_side`.
    max_dims_extra : int
        Maximum number of extra dimensions that can be appended on left of
        arrays for broadcasting. This should be kept small as the memory used
        grows exponentially with extra dimensions. By default, no extra
        dimensions are added.

    Returns
    -------
    res : tuple(:class:`numpy:numpy.ndarray`)
        Resulting ndarrays with shapes consistent with `signature` and elements
        from `elements`. Extra dimensions for broadcasting will be present.

    Examples
    --------
    .. code-block:: pycon

      >>> from hypothesis.extra.gufunc import BCAST_DIM
      >>> from hypothesis.strategies import integers, booleans
      >>> gufunc_args('(m,n),(n)->(m)',
                      dtype=np.int_, elements=integers(0, 9), max_side=3,
                      min_side={'m': 1, 'n': 2, BCAST_DIM: 3}).example()
      (array([[9, 8, 1],
              [1, 7, 1]]), array([5, 6, 5]))
      >>> gufunc_args('(m,n),(n)->(m)', dtype=['bool', 'int32'],
                           elements=[booleans(), integers(0, 100)],
                           unique=[False, True], max_dims_extra=3).example()
      (array([[[[[ True,  True,  True,  True,  True],
                 [False,  True,  True,  True, False]]]]], dtype=bool),
       array([67, 43,  0, 34, 66], dtype=int32))

    """
    shape_st = gufunc_arg_shapes(
        signature,
        excluded=excluded,
        min_side=min_side,
        max_side=max_side,
        max_dims_extra=max_dims_extra,
    )
    return _tuple_of_arrays(shape_st, dtype=dtype, elements=elements, unique=unique)
