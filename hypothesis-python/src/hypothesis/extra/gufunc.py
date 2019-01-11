# This module uses the numpy parser of the Generalized Universal Function API
# signatures `_parse_gufunc_signature`, which is only available in
# numpy>=1.12.0 and therefore requires a bump in the requirements for
# hypothesis.
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

# Key used in min_side and max_side to indicate min/max on broadcasted dims,
# using ``object()`` trick to create unique sentinel.
BCAST_DIM = object()
# Value used in default dict for max side if variable not specified
DEFAULT_MAX_SIDE = 5


def order_check_min_max(min_dict, max_dict, floor=0):
    '''Wrapper around argument checker in `hypothesis.extra.numpy`.'''
    order_check("side default", floor,
                min_dict.default_factory(), max_dict.default_factory())

    for kk in (set(min_dict.keys()) | set(max_dict.keys())):
        order_check("side %s" % kk, floor, min_dict[kk], max_dict[kk])


def _int_or_dict(x, default_val):
    '''Pre-process cases where argument `x` can be `int` or `dict`. In all
    cases, build a `defaultdict` and return it.
    '''
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
        assert default_val == x, '%s not representable as int' % str(x)
        D = defaultdict(lambda: default_val)
    # case 4: if can't be converted to dict or int, then exception raised
    return D


@composite
def _arrays(draw, dtype, shape, elements=None, unique=False):
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
    n = len(shapes)

    # Need this since broadcast_to does not like vars of type type
    if isinstance(dtype, type):
        dtype = [dtype]
    dtype = np.broadcast_to(dtype, (n,))

    elements = np.broadcast_to(elements, (n,))
    unique = np.broadcast_to(unique, (n,))

    res = tuple(draw(_arrays(dd, ss, elements=ee, unique=uu))
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
    min_side = _int_or_dict(min_side, 0)
    max_side = _int_or_dict(max_side, DEFAULT_MAX_SIDE)
    order_check_min_max(min_side, max_side)

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
    min_side : int or dict
        Minimum size of any side of the arrays. It is good to test the corner
        cases of 0 or 1 sized dimensions when applicable, but if not, a min
        size can be supplied here. Minimums can be provided on a per-dimension
        basis using a dict, e.g. ``min_side={'n': 2}``.
    max_side : int or dict
        Maximum size of any side of the arrays. This can usually be kept small
        and still find most corner cases in testing. Dictionaries can be
        supplied as with `min_side`.

    Returns
    -------
    res : tuple of ndarrays
        Resulting ndarrays with shapes consistent with `signature` and elements
        from `elements`.

    Examples
    --------

    .. code-block:: pycon

      >>> from hypothesis.strategies import integers, booleans
      >>> gufunc('(m,n),(n)->(m)', dtype=np.int_, elements=integers(0, 9),
                 min_side={'m': 1, 'n': 2}, max_side=3).example()
      (array([[2, 2, 7],
              [4, 2, 2],
              [2, 2, 2]]), array([2, 2, 2]))
      >>> gufunc('(m,n),(n)->(m)', dtype=['bool', 'int32'],
                 elements=[booleans(), integers(0, 100)],
                 unique=[False, True]).example()
      (array([[ True],
              [False],
              [ True]], dtype=bool), array([17], dtype=int32))
    """
    # Leaving dtype and elements as required for now since that leaves us the
    # flexibility to later make the default float and floats, or perhaps None
    # for a random dtype + from_dtype() strategy.
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
        grows exponentially with extra dimensions.

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
    min_side = _int_or_dict(min_side, 0)
    max_side = _int_or_dict(max_side, DEFAULT_MAX_SIDE)
    order_check_min_max(min_side, max_side)
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
    mask = draw(_arrays(np.bool, (len(shapes), n_extra)))

    # Build 2D array with extra dimensions
    extra_dim_gen = integers(min_value=min_side[BCAST_DIM],
                             max_value=max_side[BCAST_DIM])
    # e.g., extra_dims = [2 5]
    extra_dims = draw(_arrays(np.int, (n_extra,), elements=extra_dim_gen))
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
        grows exponentially with extra dimensions.

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
    shapes = draw(gufunc_broadcast_shape(signature, excluded=excluded,
                                         min_side=min_side, max_side=max_side,
                                         max_dims_extra=max_dims_extra))
    res = draw(_tuple_of_arrays(shapes, dtype=dtype,
                                elements=elements, unique=unique))
    return res


def broadcasted(f, signature, otypes, itypes, elements, unique=False,
                excluded=(), min_side=0, max_side=5, max_dims_extra=2):
    """Strategy that makes it easy to test the broadcasting semantics of a
    function against the 'ground-truth' broadcasting convention provided by
    :obj:`numpy.vectorize`.

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
    otypes : list of dtype
        The dtype for the the outputs of `f`. It must be a list with one dtype
        for each output argument of `f`. It must be a singleton list if `f`
        only returns a single output. It can also be set to `None` to leave it
        to be inferred, but this can create issues with empty arrays, so it is
        not officially supported here.
    itypes : list-like of dtype
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
        grows exponentially with extra dimensions.

    Returns
    -------
    f : callable
        This is the original function handles broadcasting itself.
    f_vec : callable
        Function that should be functionaly equivalent to `f` but broadcasting
        is handled by :obj:`numpy.vectorize`.
    res : tuple of ndarrays
        Resulting ndarrays with shapes consistent with `signature`. Extra
        dimensions for broadcasting will be present.

    Examples
    --------

    .. code-block:: pycon

      >>> import numpy as np
      >>> from hypothesis.strategies import integers, booleans
      >>> broadcasted(np.add, '(),()->()', ['int64'], ['int64', 'bool'],
                      elements=[integers(0,9), booleans()],
                      unique=[True, False]).example()
      (<ufunc 'add'>,
       <numpy.lib.function_base.vectorize at 0x11a777690>,
       (array([5, 6]), array([ True], dtype=bool)))
      >>> broadcasted(np.add, '(),()->()', ['int64'], ['int64', 'bool'],
                      elements=[integers(0,9), booleans()],
                      excluded=(1,)).example()
      (<ufunc 'add'>,
       <numpy.lib.function_base.vectorize at 0x11a715b10>,
       (array([9]), array(True, dtype=bool)))
      >>> broadcasted(np.add, '(),()->()', ['int64'], ['int64', 'bool'],
                      elements=[integers(0,9), booleans()],
                      min_side=1, max_side=3, max_dims_extra=1).example()
      (<ufunc 'add'>,
       <numpy.lib.function_base.vectorize at 0x11a7e85d0>,
       (array([7]), array([ True], dtype=bool)))
    """
    # cache and doc not needed for property testing, excluded not actually
    # needed here because we don't generate extra dims for the excluded args.
    # Using the excluded argument in np.vectorize only seems to confuse it in
    # corner cases.
    f_vec = np.vectorize(f, signature=signature, otypes=otypes)

    broadcasted_args = \
        gufunc_broadcast(signature, itypes, elements, unique=unique,
                         excluded=excluded, min_side=min_side,
                         max_side=max_side, max_dims_extra=max_dims_extra)
    funcs_and_args = tuples(just(f), just(f_vec), broadcasted_args)
    return funcs_and_args


@composite
def axised(draw, f, signature, itypes, elements, unique=False,
           min_side=1, max_side=5, max_dims_extra=2, allow_none=True):
    """Strategy that makes it easy to test the broadcasting semantics of a
    function against the 'ground-truth' broadcasting convention provided by
    :func:`numpy.apply_along_axis`.

    Parameters
    ----------
    f : callable
        This is the original function with the form f(..., axis=None). It must
        return a single `ndarray` as output.
    signature : str
        Signature for shapes to be compatible with. Expects string in format
        of numpy generalized universal function signature. This does not
        include the axis kwarg. For testing axis, the core dimension of the
        first argument must be 1D. For, :func:`numpy.mean` we use the signature
        `'(n)->()'` or for :func:`numpy.percentile` we use `'(n),()->()'`.
        Officially, only supporting ascii characters on Py3.
    itypes : list-like of dtype
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
    min_side : int or dict
        Minimum size of any side of the arrays. It is good to test the corner
        cases of 0 or 1 sized dimensions when applicable, but if not, a min
        size can be supplied here. Minimums can be provided on a per-dimension
        basis using a dict, e.g. ``min_side={'n': 2}``. One can use, e.g.,
        ``min_side={hypothesis.extra.gufunc.BCAST_DIM: 2}`` to limit the size
        of the extra dimensions of the first argument.
    max_side : int or dict
        Maximum size of any side of the arrays. This can usually be kept small
        and still find most corner cases in testing. Dictionaries can be
        supplied as with `min_side`.
    max_dims_extra : int
        Maximum number of extra dimensions that can be appended on left of
        arrays for broadcasting. This should be kept small as the memory used
        grows exponentially with extra dimensions.
    allow_none : bool
        If True, sometimes creates test cases where the axis argument is
        `None`, which implies the first argument should be flattened before
        use.

    Returns
    -------
    f : callable
        This is the original function handles axis itself.
    f_vec : callable
        Function that should be functionaly equivalent to `f` but axis is
        handled by :func:`numpy.apply_along_axis`.
    args : tuple of ndarrays
        Arguments to pass to `f` not including the axis kwarg. Extra dimensions
        will be added to first argument (args[0]) to test axis slicing.
    axis : int
        Axis along which first argument of `f` is sliced.

    Examples
    --------

    .. code-block:: pycon

      >>> import numpy as np
      >>> from hypothesis.strategies import integers, floats
      >>> axised(np.percentile, '(n),()->()', ['int64', np.float_],
                 elements=[integers(0, 9), floats(0, 1)],
                 unique=True).example()
      (<function numpy.lib.function_base.percentile>,
       <function __main__.f_axis>,
       (array([9, 0, 1, 2, 8]), array(0.6318185150011054)),
       None)
      >>> axised(np.percentile, '(n),()->()', ['int64', np.float_],
                 elements=[integers(0, 9), floats(0, 1)],
                 allow_none=False).example()
          (<function numpy.lib.function_base.percentile>,
           <function __main__.f_axis>,
           (array([[[2, 2],
                    [2, 2]]]), array(0.34600973310654154)),
           0)
    """
    min_side = _int_or_dict(min_side, 1)
    max_side = _int_or_dict(max_side, DEFAULT_MAX_SIDE)
    order_check_min_max(min_side, max_side, floor=1)

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
    args = draw(_tuple_of_arrays(shapes, dtype=itypes,
                                 elements=elements, unique=unique))

    funcs_and_args = (f, f_axis, args, axis)
    return funcs_and_args
