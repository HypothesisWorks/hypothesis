# This module uses the numpy parser of the Generalized Universal Function API
# signatures `_parse_gufunc_signature`, which is only available in
# numpy>=1.12.0 and therefore requires a bump in the requirements for
# hypothesis.
# TODO rename this file private and then import to numpy
from __future__ import absolute_import, division, print_function

from collections import defaultdict

import numpy as np
import numpy.lib.function_base as npfb

from hypothesis.extra.numpy import arrays, order_check
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.strategies import builds, composite, integers, just, fixed_dictionaries

# Should not ever need to broadcast beyond this, but should be able to set it
# as high as 32 before breaking assumptions in numpy.
GLOBAL_DIMS_MAX = 12

# Key used in min_side and max_side to indicate min/max on broadcasted dims,
# using ``object()`` trick to create unique sentinel.
BCAST_DIM = object()
# Value used in default dict for max side if variable not specified
DEFAULT_MAX_SIDE = 5

# TODO isort

# TODO tester that transforms somes elements in list with just, or applies
# just if not iterable

# TODO check doc string examples with rand seed = 0

# TODO consider in tests using from_regex(npfb._SIGNATURE)

# TODO doc strings need to be redone with interface change

# Maybe note dtype could be built in type


def order_check_min_max(min_dict, max_dict, floor=0):
    """Wrapper around argument checker in `hypothesis.extra.numpy`."""
    order_check("side default", floor,
                min_dict.default_factory(), max_dict.default_factory())

    for kk in (set(min_dict.keys()) | set(max_dict.keys())):
        order_check("side %s" % kk, floor, min_dict[kk], max_dict[kk])


def _int_or_dict(x, default_val):
    """Pre-process cases where argument `x` can be `int`, `dict`, or
    `defaultdict`. In all cases, build a `defaultdict` and return it.
    """
    # case 1: x already defaultdict, leave it be, pass thru
    if isinstance(x, defaultdict):
        return x

    default_val = int(default_val)  # Make sure simple int
    try:
        # case 2: x is or can be converted to dict
        D = defaultdict(lambda: default_val, x)
    except TypeError:
        # case 3: x is or can be converted to int => make a const dict
        default_val = int(x)  # Make sure simple int
        # TODO use arg check
        assert default_val == x, "%s not representable as int" % str(x)
        D = defaultdict(lambda: default_val)
    # case 4: if can't be converted to dict or int, then exception raised
    return D


@composite
def _arrays(draw, dtype, shape, elements=None, unique=False):
    """Wrapper to fix issues with `hypothesis.extra.numpy.arrays`.

    `arrays` is strict on shape being `int` which this fixes. This is partially
    not needed in Py3 since there is no `int` vs `long` issue. Also, `arrays`
    does not return ndarray for 0-dim arrays.

    This could possibly be done more compactly with:
    ```
    S = builds(np.asarray,
               arrays(dtype, shape, elements=elements, unique=unique),
               dtype=just(dtype))
    ```
    However, this appears to be slower.
    """
    # TODO swap order draw dtype
    shape = tuple(int(aa) for aa in shape)
    S = arrays(dtype, shape, elements=elements, unique=unique).map(np.asarray)
    X = draw(S)
    X = X.astype(dtype, copy=False)  # Will never see original => copy=False
    return X


@composite
def _tuple_of_arrays(draw, shapes, dtype, elements, unique=False):
    """Strategy to generate a tuple of ndarrays with specified shapes.

    Parameters
    ----------
    shapes : list-like of tuples
        List of tuples where each tuple is the shape of an argument. A
        `SearchStrategy` for list of tuples is also supported.
    dtype : list-like of dtype
        List of numpy `dtype` for each argument. These can be either strings
        (``'int64'``), type (``np.int64``), or numpy `dtype`
        (``np.dtype('int64')``). A single `dtype` can be supplied for all
        arguments.
    elements : list-like of strategy
        Strategies to fill in array elements on a per argument basis. One can
        also specify a single strategy
        (e.g., :func:`hypothesis.strategies.floats`)
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
    # TODO file np bug report on this
    if isinstance(dtype, type):
        dtype = [dtype]
    dtype = np.broadcast_to(dtype, (n,))

    elements = np.broadcast_to(elements, (n,))
    unique = np.broadcast_to(unique, (n,))

    # This could somewhat easily be done using builds and avoid need for
    # composite if shape is always given and not strategy. Otherwise, we need
    # to chain strategies and probably not worth the effort.
    res = tuple(draw(_arrays(dd, ss, elements=ee, unique=uu))
                for dd, ss, ee, uu in zip(dtype, shapes, elements, unique))
    return res


def _signature_map(map_dict, parsed_sig):
    '''Map values found in parsed gufunc signature.'''
    # TODO tests (inverse + const)
    shapes = [tuple(map_dict[k] for k in arg) for arg in parsed_sig]
    return shapes


def _gufunc_arg_shapes(inp, min_side=0, max_side=5):
    """Strategy to generate array shapes for arguments to a function consistent
    with its signature.

    Parameters
    ----------
    signature : str
        Signature for shapes to be compatible with. Expects string in format
        of numpy generalized universal function signature, e.g.,
        `'(m,n),(n)->(m)'` for vectorized matrix-vector multiplication.
        Officially, only supporting ascii characters on Py3.
    min_side : int or dict
        Minimum size of any side of the arrays. It is good to test the corner
        cases of 0 or 1 sized dimensions when applicable, but if not, a min
        size can be supplied here. Minimums can be provided on a per-dimension
        basis using a dict, e.g. ``min_side={'n': 2}``.
    max_side : int or dict
        Maximum size of any side of the arrays. This can usually be kept small
        and still find most corner cases in testing. Dictionaries can also be
        supplied as with `min_side`.

    Returns
    -------
    shapes : list of tuples
        list of tuples where each tuple is the shape of an argument.

    Examples
    --------

    .. code-block:: pycon

      >>> gufunc_shape('(m,n),(n)->(m)',
                       min_side={'m': 1, 'n': 2}, max_side=3).example()
      [(3, 2), (2,)]
    """
    # Skipping validation on min and max sides since this function is private.
    # TODO put in doc string must be default dicts

    # Get all dimension names in signature, including numeric constants
    all_dimensions = set([k for arg in inp for k in arg])

    # Note that isdigit can be a bit odd with some unicode characters
    # => officially only support ascii characters in signature.
    dim_map_st = {k: (just(int(k)) if k.isdigit() else
                      integers(min_value=min_side[k], max_value=max_side[k]))
                  for k in all_dimensions}

    # Could strategy that draws ints for dimensions and subs them in
    S = builds(_signature_map,
               map_dict=fixed_dictionaries(dim_map_st), parsed_sig=just(inp))
    return S

# TODO validate:
# excluded iterable (__contains__), sig


@composite
def gufunc_arg_shapes(draw, signature, excluded=(),
                      min_side=0, max_side=5, max_dims_extra=0):
    """Strategy to generate the shape of ndarrays for arguments to a function
    consistent with its signature with extra dimensions to test broadcasting.

    Parameters
    ----------
    signature : str
        Signature for shapes to be compatible with. Expects string in format
        of numpy generalized universal function signature, e.g.,
        `'(m,n),(n)->(m)'` for vectorized matrix-vector multiplication.
        Officially, only supporting ascii characters on Py3.
    excluded : list-like of integers
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
    shapes : list of tuples
        list of tuples where each tuple is the shape of an argument. Extra
        dimensions for broadcasting will be present in the shapes.

    Examples
    --------

    .. code-block:: pycon

      >>> from hypothesis.extra.gufunc import BCAST_DIM
      >>> gufunc_broadcast_shape('(m,n),(n)->(m)', max_side=9,
                                 min_side={'m': 1, 'n': 2, BCAST_DIM: 5},
                                 max_dims_extra=3).example()
      [(9, 4), (7, 1, 4)]
      >>> gufunc_broadcast_shape('(m,n),(n)->(m)', excluded=(0,), max_side=9,
                                 max_dims_extra=3).example()
      [(3, 6), (2, 6)]
    """
    # TODO broadcasted needs to use diff default for extra dims, check uses in
    # tests.
    min_side = _int_or_dict(min_side, 0)
    max_side = _int_or_dict(max_side, DEFAULT_MAX_SIDE)
    order_check_min_max(min_side, max_side)
    order_check("extra dims", 0, max_dims_extra, GLOBAL_DIMS_MAX)

    # Parse out the signature: e.g., parses to [('n', 'm'), ('m', 'p')]
    # Warning: this uses "private" function of numpy, but it does the job.
    # Should also check signature.isascii() since there are lot of weird corner
    # cases with unicode parsing, but isascii() restricts us to Py >=3.7.
    inp, out = npfb._parse_gufunc_signature(signature)

    # Get core shapes before broadcasted dimensions
    # e.g., shapes = [(1, 3), (3, 1)]
    shapes = draw(_gufunc_arg_shapes(inp,
                                     min_side=min_side, max_side=max_side))
    # Should not be possible if signature parser makes sense
    assert len(shapes) > 0

    # If we are not looking for this extra broadcasting dims craziness just
    # return the current draw.
    # TODO use > 0
    if max_dims_extra == 0:
        return shapes

    # TODO consider separate composite strat that does all this and then only
    # apply that second then if max_extra > 0
    # use builds to func that takes:
    # core_dims, extra_dims vec, mask mat, n_extra vec

    max_core_dims = max(len(ss) for ss in shapes)

    # Which extra dims will just be 1 to get broadcasted, specified by mask
    n_extra = draw(integers(min_value=0, max_value=max_dims_extra))  # e.g., 2
    # Make sure always under global max dims
    # TODO max with zero, TODO set GLOBAL DIMS MAX low and run tests
    # TODO make a list of max for each arg
    n_extra = min(n_extra, GLOBAL_DIMS_MAX - max_core_dims)
    # TODO consider just setting n_extra to max_extra
    # e.g., mask = [[True False], [False False]]
    mask = draw(_arrays(np.bool, (len(shapes), n_extra)))

    # Build 2D array with extra dimensions
    extra_dim_gen = integers(min_value=min_side[BCAST_DIM],
                             max_value=max_side[BCAST_DIM])
    # e.g., extra_dims = [2 5]
    # TODO consider using tuples if faster but assert dtype after tile since
    # len always greater than 0
    extra_dims = draw(_arrays(np.int, (n_extra,), elements=extra_dim_gen))
    # e.g., extra_dims = [[2 5], [2 5]]
    extra_dims = np.tile(extra_dims, (len(shapes), 1))
    # e.g., extra_dims = [[1 5], [2 5]]
    extra_dims[mask] = 1  # This may be outside [min_side, max_side]

    # How many extra dims on left to include for each argument (implicitly) 1
    # for each chopped dim. Cannot include any extra for excluded arguments.
    # e.g., n_extra_per_arg = [1, 2]
    # TODO consider clipping with global max here instead
    n_extra_per_arg = [0 if nn in excluded else
                       draw(integers(min_value=0, max_value=n_extra))
                       for nn in range(len(shapes))]

    # TODO note broadcasted dims of np type and not native, do we care??
    # Can do tolist() first if we care, comment either way
    # TODO write check in tests

    # Get full dimensions (core+extra), will chop some on left randomly
    # e.g., shapes = [(5, 1, 3), (2, 5, 3, 1)]
    # We use pp[len(pp) - nn:] instead of pp[-nn:] since that doesn't handle
    # corner case with nn=0 correctly (seems like an oversight of py slicing).
    shapes = [tuple(pp[len(pp) - nn:]) + ss
              for ss, pp, nn in zip(shapes, extra_dims, n_extra_per_arg)]
    return shapes


def gufunc_args(signature, dtype, elements, unique=False, excluded=(),
                min_side=0, max_side=5, max_dims_extra=0):
    """Strategy to generate a tuple of ndarrays for arguments to a function
    consistent with its signature with extra dimensions to test broadcasting.

    Parameters
    ----------
    signature : str
        Signature for shapes to be compatible with. Expects string in format
        of numpy generalized universal function signature, e.g.,
        `'(m,n),(n)->(m)'` for vectorized matrix-vector multiplication.
        Officially, only supporting ascii characters on Py3.
    dtype : list-like of dtype
        List of numpy `dtype` for each argument. These can be either strings
        (``'int64'``), type (``np.int64``), or numpy `dtype`
        (``np.dtype('int64')``). A single `dtype` can be supplied for all
        arguments.
    elements : list-like of strategy
        Strategies to fill in array elements on a per argument basis. One can
        also specify a single strategy
        (e.g., :func:`hypothesis.strategies.floats`)
        and have it applied to all arguments.
    unique : list-like of bool
        Boolean flag to specify if all elements in an array must be unique.
        One can also specify a single boolean to apply it to all arguments.
    excluded : list-like of integers
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
    res : tuple of ndarrays
        Resulting ndarrays with shapes consistent with `signature` and elements
        from `elements`. Extra dimensions for broadcasting will be present.

    Examples
    --------

    .. code-block:: pycon

      >>> from hypothesis.extra.gufunc import BCAST_DIM
      >>> from hypothesis.strategies import integers, booleans
      >>> gufunc_broadcast('(m,n),(n)->(m)', dtype=np.int_,
                           elements=integers(0, 9), max_side=3,
                           min_side={'m': 1, 'n': 2, BCAST_DIM: 3}).example()
      (array([[[2, 2, 2],
               [3, 2, 2],
               [2, 0, 2]]]), array([[[4, 4, 4]]]))
      >>> gufunc_broadcast('(m,n),(n)->(m)', dtype=['bool', 'int32'],
                           elements=[booleans(), integers(0, 100)],
                           unique=[False, True], max_dims_extra=3).example()
      (array([[[ True,  True,  True],
               [ True,  True,  True]]], dtype=bool), array([[[51, 75, 78],
               [98, 99, 50]]], dtype=int32))
    """
    shape_st = gufunc_arg_shapes(signature, excluded=excluded,
                                 min_side=min_side, max_side=max_side,
                                 max_dims_extra=max_dims_extra)
    S = _tuple_of_arrays(shape_st,
                         dtype=dtype, elements=elements, unique=unique)
    return S
