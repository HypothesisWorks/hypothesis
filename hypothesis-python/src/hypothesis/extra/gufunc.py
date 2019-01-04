"""Extend hypothesis.extra.numpy for functions that follow the GU function API.

This routine uses the numpy parser of the Generalized Universal Function API
signatures `_parse_gufunc_signature`, which is only available in numpy>=1.12.0
and therefore requires a bump in the requirements for hypothesis.
"""
from __future__ import absolute_import, division, print_function

from collections import defaultdict

import numpy as np
import numpy.lib.function_base as npfb

from hypothesis.extra.numpy import arrays, check_argument, order_check
from hypothesis.strategies import (
    booleans,
    composite,
    integers,
    just,
    lists,
    tuples,
)

# Should not ever need to broadcast beyond this, but should be able to set it
# as high as 32 before breaking assumptions in numpy.
GLOBAL_DIMS_MAX = 12

# Key used in min_side and max_side to indicate min/max on broadcasted dims
# TODO consider using a fancy enum or something
BCAST_DIM = None
# Value used in default dict for max side if variable not specified
DEFAULT_MAX_SIDE = 5


def int_or_dict(x, default_val):
    if isinstance(x, defaultdict):
        return x  # pass thru

    default_val = int(default_val)  # Make sure simple int
    # TODO tests
    try:
        D = defaultdict(lambda: default_val, x)
    except TypeError:  # ==> x is int
        default_val = int(x)  # Make sure simple int
        D = defaultdict(lambda: default_val)
    return D


@composite
def arrays_(draw, dtype, shape, elements=None, unique=False):
    """Wrapper to fix issues with `hypothesis.extra.numpy.arrays`.

    `arrays` is strict on shape being `int` which this fixes. This is partially
    not needed in Py3 since there is no `int` vs `long` issue. Also, `arrays`
    does not return ndarray for 0-dim arrays.
    """
    shape = tuple(int(aa) for aa in shape)
    S = arrays(dtype, shape, elements=elements, unique=unique).map(np.asarray)
    X = draw(S)
    X = X.astype(dtype)
    return X


@composite
def _tuple_of_arrays(draw, shapes, dtype, elements, unique=False):
    """Strategy to generate a tuple of ndarrays with specified shapes.

    Parameters
    ----------
    shapes : list-like of tuples
        List of tuples where each tuple is the shape of an argument.
    filler : strategy
        Strategy to fill in array elements e.g. `hypothesis.strategies.floats`.
        The parameters for `filler` are specified by the `kwargs`.
    kwargs : kwargs
        Passed to filler strategy.

    Returns
    -------
    res : tuple of ndarrays
        Resulting ndarrays with shape from `shapes` and elements from `filler`.
    """
    n = len(shapes)

    # TODO tests need to type raw type, dtype and str
    # Need this since broadcast_to does not like vars of type type
    if isinstance(dtype, type):
        dtype = [dtype]
    dtype = np.broadcast_to(dtype, (n,))

    elements = np.broadcast_to(elements, (n,))
    unique = np.broadcast_to(unique, (n,))

    res = tuple(draw(arrays_(dd, ss, elements=ee, unique=uu))
                for dd, ss, ee, uu in zip(dtype, shapes, elements, unique))
    return res


@composite
def gufunc_shape(draw, signature, min_side=0, max_side=5):
    """Strategy to generate array shapes for arguments to a function consistent
    with its signature.

    Parameters
    ----------
    signature : str
        Signature for shapes to be compatible with. Expects string in format
        of numpy generalized universal function signature, e.g.,
        `'(m,n),(n)->(m)'` for vectorized matrix-vector multiplication.
        Officially, only supporting ascii characters on Py3.
    min_side : int
        Minimum size of any side of the arrays. It is good to test the corner
        cases of 0 or 1 sized dimensions when applicable, but if not, a min
        size can be supplied here.
    max_side : int
        Maximum size of any side of the arrays. This can usually be kept small
        and still find most corner cases in testing.

    Returns
    -------
    shapes : list of tuples
        list of tuples where each tuple is the shape of an argument.

    See Also
    --------
    See `numpy.vectorize` at
    docs.scipy.org/doc/numpy-1.14.0/reference/generated/numpy.vectorize.html
    """
    # TODO figure out how to order check this
    min_side = int_or_dict(min_side, 0)
    max_side = int_or_dict(max_side, DEFAULT_MAX_SIDE)

    # We should check signature.isascii() since there are lot of weird corner
    # cases with unicode parsing, but isascii() restricts us to Py >=3.7.

    # Parse out the signature
    # Warning: this uses "private" function of numpy, but it does the job.
    # parses to [('n', 'm'), ('m', 'p')]
    # This parsing currently occurs every draw and build be pulled out to only
    # occur once with some code reorganization. Some of the dictionary D could
    # be done that way as well.
    inp, out = npfb._parse_gufunc_signature(signature)

    # Randomly sample dimensions for each variable, if literal number provided
    # just put the integer in, e.g., D['2'] = 2 if someone provided '(n,2)'.
    # e.g., D = {'p': 1, 'm': 3, 'n': 1}
    D = {k: (int(k) if k.isdigit() else
             draw(integers(min_value=min_side[k], max_value=max_side[k])))
         for arg in inp for k in arg}

    # Build the shapes: e.g., shapes = [(1, 3), (3, 1)]
    shapes = [tuple(D[k] for k in arg) for arg in inp]

    return shapes


@composite
def gufunc(draw, signature, dtype, elements, unique=False,
           min_side=0, max_side=5):
    """Strategy to generate a tuple of ndarrays for arguments to a function
    consistent with its signature.

    Parameters
    ----------
    signature : str
        Signature for shapes to be compatible with. Expects string in format
        of numpy generalized universal function signature, e.g.,
        `'(m,n),(n)->(m)'` for vectorized matrix-vector multiplication.
        Officially, only supporting ascii characters on Py3.
    filler : strategy
        Strategy to fill in array elements e.g. `hypothesis.strategies.floats`.
        The parameters for `filler` are specified by the `kwargs`.
    min_side : int
        Minimum size of any side of the arrays. It is good to test the corner
        cases of 0 or 1 sized dimensions when applicable, but if not, a min
        size can be supplied here.
    max_side : int
        Maximum size of any side of the arrays. This can usually be kept small
        and still find most corner cases in testing.
    kwargs : kwargs
        Passed to filler strategy.

    Returns
    -------
    res : tuple of ndarrays
        Resulting ndarrays with shapes consistent with `signature` and elements
        from `filler`.

    See Also
    --------
    See `numpy.vectorize` at
    docs.scipy.org/doc/numpy-1.14.0/reference/generated/numpy.vectorize.html
    """
    shapes = draw(gufunc_shape(signature,
                               min_side=min_side, max_side=max_side))
    res = draw(_tuple_of_arrays(shapes, dtype=dtype,
                                elements=elements, unique=unique))
    return res


@composite
def gufunc_broadcast_shape(draw, signature, excluded=(),
                           min_side=0, max_side=5, max_dims_extra=2):
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
        not be vectorized. Uses same format as `numpy.vectorize`.
    min_side : int
        Minimum size of any side of the arrays. It is good to test the corner
        cases of 0 or 1 sized dimensions when applicable, but if not, a min
        size can be supplied here. Note that the broadcasted dimensions may be
        1 even regardless of `min_side` or `max_side`.
    max_side : int
        Maximum size of any side of the arrays. This can usually be kept small
        and still find most corner cases in testing.
    max_dims_extra : int
        Maximum number of extra dimensions that can be appended on left of
        arrays for broadcasting. This should be kept small as the memory used
        grows exponentially with extra dimensions.

    Returns
    -------
    shapes : list of tuples
        list of tuples where each tuple is the shape of an argument. Extra
        dimensions for broadcasting will be present in the shapes.

    See Also
    --------
    See `numpy.vectorize` at
    docs.scipy.org/doc/numpy-1.14.0/reference/generated/numpy.vectorize.html
    """
    # TODO still need order check
    min_side = int_or_dict(min_side, 0)
    max_side = int_or_dict(max_side, DEFAULT_MAX_SIDE)
    order_check("extra dims", 0, max_dims_extra, GLOBAL_DIMS_MAX)

    # Get core shapes before broadcasted dimensions
    # e.g., shapes = [(1, 3), (3, 1)]
    shapes = draw(gufunc_shape(signature,
                               min_side=min_side, max_side=max_side))
    # Should not be possible if signature parser makes sense
    assert len(shapes) > 0

    max_core_dims = max(len(ss) for ss in shapes)

    # Which extra dims will just be 1 to get broadcasted, specified by mask
    n_extra = draw(integers(min_value=0, max_value=max_dims_extra))  # e.g., 2
    # Make sure always under global max dims
    n_extra = min(n_extra, GLOBAL_DIMS_MAX - max_core_dims)
    # e.g., mask = [[True False], [False False]]
    mask = draw(arrays_(np.bool, (len(shapes), n_extra)))

    # Build 2D array with extra dimensions
    extra_dim_gen = integers(min_value=min_side[BCAST_DIM],
                             max_value=max_side[BCAST_DIM])
    # e.g., extra_dims = [2 5]
    extra_dims = draw(arrays_(np.int, (n_extra,), elements=extra_dim_gen))
    # e.g., extra_dims = [[2 5], [2 5]]
    extra_dims = np.tile(extra_dims, (len(shapes), 1))
    # e.g., extra_dims = [[1 5], [2 5]]
    extra_dims[mask] = 1  # This may be outside [min_side, max_side]

    # How many extra dims on left to include for each argument (implicitly) 1
    # for each chopped dim. Cannot include any extra for excluded arguments.
    # e.g., n_extra_per_arg = [1, 2]
    n_extra_per_arg = [0 if nn in excluded else
                       draw(integers(min_value=0, max_value=n_extra))
                       for nn in range(len(shapes))]

    # Get full dimensions (core+extra), will chop some on left randomly
    # e.g., shapes = [(5, 1, 3), (2, 5, 3, 1)]
    # We use pp[len(pp) - nn:] instead of pp[-nn:] since that doesn't handle
    # corner case with nn=0 correctly (seems like an oversight of py slicing).
    shapes = [tuple(pp[len(pp) - nn:]) + ss
              for ss, pp, nn in zip(shapes, extra_dims, n_extra_per_arg)]
    return shapes


@composite
def gufunc_broadcast(draw, signature, dtype, elements, unique=False,
                     excluded=(), min_side=0, max_side=5, max_dims_extra=2):
    """Strategy to generate a tuple of ndarrays for arguments to a function
    consistent with its signature with extra dimensions to test broadcasting.

    Parameters
    ----------
    signature : str
        Signature for shapes to be compatible with. Expects string in format
        of numpy generalized universal function signature, e.g.,
        `'(m,n),(n)->(m)'` for vectorized matrix-vector multiplication.
        Officially, only supporting ascii characters on Py3.
    filler : strategy
        Strategy to fill in array elements e.g. `hypothesis.strategies.floats`.
        The parameters for `filler` are specified by the `kwargs`.
    excluded : list-like of integers
        Set of integers representing the positional for which the function will
        not be vectorized. Uses same format as `numpy.vectorize`.
    min_side : int
        Minimum size of any side of the arrays. It is good to test the corner
        cases of 0 or 1 sized dimensions when applicable, but if not, a min
        size can be supplied here. Note that the broadcasted dimensions may be
        1 even regardless of `min_side` or `max_side`.
    max_side : int
        Maximum size of any side of the arrays. This can usually be kept small
        and still find most corner cases in testing.
    max_dims_extra : int
        Maximum number of extra dimensions that can be appended on left of
        arrays for broadcasting. This should be kept small as the memory used
        grows exponentially with extra dimensions.
    kwargs : kwargs
        Passed to filler strategy.

    Returns
    -------
    res : tuple of ndarrays
        Resulting ndarrays with shapes consistent with `signature` and elements
        from `filler`. Extra dimensions for broadcasting will be present.

    See Also
    --------
    See `numpy.vectorize` at
    docs.scipy.org/doc/numpy-1.14.0/reference/generated/numpy.vectorize.html
    """
    shapes = draw(gufunc_broadcast_shape(signature, excluded=excluded,
                                         min_side=min_side, max_side=max_side,
                                         max_dims_extra=max_dims_extra))
    res = draw(_tuple_of_arrays(shapes, dtype=dtype,
                                elements=elements, unique=unique))
    return res


def broadcasted(f, signature, otypes, excluded=(), **kwargs):
    """Strategy that makes it easy to test the broadcasting semantics of a
    function against the 'ground-truth' broadcasting convention provided by
    `numpy.vectorize`.

    Extra parameters for `gufunc_broadcast` can be provided as `kwargs`.

    Parameters
    ----------
    f : callable
        This is the original function handles broadcasting itself. It must
        return an `ndarray` or multiple `ndarray` (which Python treats as a
        `tuple`) if returning 2-or-more output arguments.
    signature : str
        Signature for shapes to be compatible with. Expects string in format
        of numpy generalized universal function signature, e.g.,
        `'(m,n),(n)->(m)'` for vectorized matrix-vector multiplication.
        Officially, only supporting ascii characters on Py3.
    otypes : list of dtypes
        The dtypes for the the outputs of `f`. It must be a list with one dtype
        for each output argument of `f`. It must be a singleton list if `f`
        only returns a single output. It can also be set to `None` to leave it
        to be inferred, but this can create issues with empty arrays, so it is
        not officially supported here.
    excluded : list-like of integers
        Set of integers representing the positional for which the function will
        not be vectorized. Uses same format as `numpy.vectorize`.
    filler : strategy
        Strategy to fill in array elements e.g. `hypothesis.strategies.floats`.
        The parameters for `filler` are specified by the `kwargs`.
    min_side : int
        Minimum size of any side of the arrays. It is good to test the corner
        cases of 0 or 1 sized dimensions when applicable, but if not, a min
        size can be supplied here. Note that the broadcasted dimensions may be
        1 even regardless of `min_side` or `max_side`.
    max_side : int
        Maximum size of any side of the arrays. This can usually be kept small
        and still find most corner cases in testing.
    max_dims_extra : int
        Maximum number of extra dimensions that can be appended on left of
        arrays for broadcasting. This should be kept small as the memory used
        grows exponentially with extra dimensions.
    kwargs : kwargs
        Passed to filler strategy.

    Returns
    -------
    f : callable
        This is the original function handles broadcasting itself.
    f_vec : callable
        Function that should be functionaly equivalent to `f` but broadcasting
        is handled by `numpy.vectorize`.
    res : tuple of ndarrays
        Resulting ndarrays with shapes consistent with `signature`. Extra
        dimensions for broadcasting will be present.

    See Also
    --------
    See `numpy.vectorize` at
    docs.scipy.org/doc/numpy-1.14.0/reference/generated/numpy.vectorize.html
    """
    # cache and doc not needed for property testing, excluded not actually
    # needed here because we don't generate extra dims for the excluded args.
    # Using the excluded argument in np.vectorize only seems to confuse it in
    # corner cases.
    f_vec = np.vectorize(f, signature=signature, otypes=otypes)

    broadcasted_args = gufunc_broadcast(signature, excluded=excluded, **kwargs)
    funcs_and_args = tuples(just(f), just(f_vec), broadcasted_args)
    return funcs_and_args


@composite
def axised(draw, f, signature, dtype, elements, unique=False,
           min_side=1, max_side=5, max_dims_extra=2, allow_none=True):
    """Strategy that makes it easy to test the broadcasting semantics of a
    function against the 'ground-truth' broadcasting convention provided by
    `numpy.apply_along_axis`.

    Parameters
    ----------
    f : callable
        This is the original function with the form f(..., axis=None). It must
        return a single `ndarray` as output.
    signature : str
        Signature for shapes to be compatible with. Expects string in format
        of numpy generalized universal function signature. This does not
        include the axis kwarg. For testing axis, the core dimension of the
        first argument must be 1D. For, `np.mean` we use the signature
        `'(n)->()'` or for `'np.percentile'` we use `'(n),()->()'`. Officially,
        only supporting ascii characters on Py3.
    filler : strategy
        Strategy to fill in array elements e.g. `hypothesis.strategies.floats`.
        The parameters for `filler` are specified by the `kwargs`.
    min_side : int
        Minimum size of any side of the arrays. This must be >= 1 since
        `np.apply_along_axis` does not like sides of 0 for the first argument.
    min_side : int
        Minimum size of any side of the arrays. It is good to test the corner
        cases of 0 or 1 sized dimensions when applicable, but if not, it a min
        size can be supplied here.
    max_dims_extra : int
        Maximum number of extra dimensions that can be added to the first
        argument of `f`, which is the argument that `numpy.apply_along_axis`
        operates on. This should be kept small as the memory used
        grows exponentially with extra dimensions.
    allow_none : bool
        If True, sometimes creates test cases where the axis argument is None,
        which implies the first argument should be flattened before use.
    kwargs : kwargs
        Passed to filler strategy.

    Returns
    -------
    f : callable
        This is the original function handles axis itself.
    f_vec : callable
        Function that should be functionaly equivalent to `f` but axis is
        handled by `numpy.apply_along_axis`.
    args : tuple of ndarrays
        Arguments to pass to `f` not including the axis kwarg. Extra dimensions
        will be added to first argument (args[0]) to test axis slicing.
    axis : int
        Axis along which first argument of `f` is sliced.

    See Also
    --------
    See `numpy.apply_along_axis` at
    docs.scipy.org/doc/numpy-1.14.0/reference/generated/numpy.apply_along_axis.html
    See `numpy.vectorize` at
    docs.scipy.org/doc/numpy-1.14.0/reference/generated/numpy.vectorize.html
    """
    # TODO still need order check, and check min 1
    min_side = int_or_dict(min_side, 0)
    max_side = int_or_dict(max_side, DEFAULT_MAX_SIDE)

    def f_axis(X, *args, **kwargs):
        # This trick is not needed in Python3, after dropping Py2 support we
        # can change to ``f_axis(X, *args, axis=None)``.
        axis = kwargs.get("axis", None)

        if axis is None:
            Y = f(np.ravel(X), *args)
        else:
            Y = np.apply_along_axis(f, axis, X, *args)
        return Y

    side_X = integers(min_value=min_side[BCAST_DIM],
                      max_value=max_side[BCAST_DIM])
    # X has core dims (n,) so the total dims must be in [1, max_dims_extra + 1]
    X_shape = draw(lists(side_X, min_size=1, max_size=max_dims_extra + 1))

    shapes = draw(gufunc_shape(signature,
                               min_side=min_side, max_side=max_side))
    # ok to assume [0] since should not be any way to generate len(shapes) = 0
    check_argument(len(shapes[0]) == 1,
                   "first argument of signature %s must be 1D, for %dD",
                   signature, len(shapes[0]))

    assert len(shapes[0]) == 1, \
        "first argument of signature %s must be 1D" % signature

    if allow_none and draw(booleans()):
        # If function allows for axis=None, then must be able to handle
        # arbitrary shapes of first arg X (with X.ndims >= 1).
        axis = None
    else:
        # integers is inclusive => must use len(X_shape) - 1 when drawing axis
        axis = draw(integers(min_value=0, max_value=len(X_shape) - 1))
        n, = shapes[0]
        X_shape[axis] = n

    shapes[0] = X_shape
    args = draw(_tuple_of_arrays(shapes, dtype=dtype,
                                 elements=elements, unique=unique))

    funcs_and_args = (f, f_axis, args, axis)
    return funcs_and_args
