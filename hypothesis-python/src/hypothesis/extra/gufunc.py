from hypothesis.extra.numpy import arrays
from hypothesis.strategies import composite, just, lists, tuples
from hypothesis.strategies import booleans, integers, floats
import numpy as np
import numpy.lib.function_base as npfb


@composite
def tuple_of_arrays(draw, shapes, filler, **kwargs):
    '''Strategy to generate a tuple of ndarrays with specified shapes.

    Parameters
    ----------
    shapes : iterable of tuples
        Iterable of tuples where each tuple is the shape of an argument.
    filler : strategy
        Strategy to fill in array elements e.g. `hypothesis.strategies.floats`.
        The parameters for `filler` are specified by the `kwargs`.

    Returns
    -------
    res : tuple of ndarrays
        Resulting ndarrays with shape from `shapes` and elements from `filler`.
    '''
    dtype = np.dtype(type(draw(filler(**kwargs))))
    res = tuple(draw(arrays(dtype, ss, elements=filler(**kwargs)))
                for ss in shapes)
    return res


@composite
def gufunc_shape(draw, signature, min_side=0, max_side=5):
    '''Strategy to generate array shapes for arguments to a function consistent
    with its signature.

    Parameters
    ----------
    signature : str
        Signature for shapes to be compatible with. Expects string in format
        of numpy generalized universal function signature, e.g.,
        `'(m,n),(n)->(m)'` for vectorized matrix-vector multiplication.
    min_side : int
        Minimum size of any side of the arrays. It is good to test the corner
        cases of 0 or 1 sized dimensions when applicable, but if not, it a min
        size can be supplied here.
    max_side : int
        Maximum size of any side of the arrays. This can usually be kept small
        and still find most corner cases in testing.

    Returns
    ----------
    shapes : list of tuples
        list of tuples where each tuple is the shape of an argument.

    See Also
    --------
    See `numpy.vectorize` at
    docs.scipy.org/doc/numpy-1.14.0/reference/generated/numpy.vectorize.html
    '''
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
             draw(integers(min_value=min_side, max_value=max_side)))
         for arg in inp for k in arg}

    # Build the shapes: e.g., shapes = [(1, 3), (3, 1)]
    shapes = [tuple(D[k] for k in arg) for arg in inp]
    return shapes


@composite
def gufunc(draw, signature, filler=floats, min_side=0, max_side=5, **kwargs):
    '''Strategy to generate a tuple of ndarrays for arguments to a function
    consistent with its signature.

    Parameters
    ----------
    signature : str
        Signature for shapes to be compatible with. Expects string in format
        of numpy generalized universal function signature, e.g.,
        `'(m,n),(n)->(m)'` for vectorized matrix-vector multiplication.
    filler : strategy
        Strategy to fill in array elements e.g. `hypothesis.strategies.floats`.
        The parameters for `filler` are specified by the `kwargs`.
    min_side : int
        Minimum size of any side of the arrays. It is good to test the corner
        cases of 0 or 1 sized dimensions when applicable, but if not, it a min
        size can be supplied here.
    max_side : int
        Maximum size of any side of the arrays. This can usually be kept small
        and still find most corner cases in testing.

    Returns
    -------
    res : tuple of ndarrays
        Resulting ndarrays with shapes consistent with `signature` and elements
        from `filler`.

    See Also
    --------
    See `numpy.vectorize` at
    docs.scipy.org/doc/numpy-1.14.0/reference/generated/numpy.vectorize.html
    '''
    shapes = draw(gufunc_shape(signature,
                               min_side=min_side, max_side=max_side))
    res = draw(tuple_of_arrays(shapes, filler, **kwargs))
    return res


@composite
def gufunc_broadcast_shape(draw, signature,
                           excluded=(), min_side=0, max_side=5, max_extra=2):
    '''Strategy to generate the shape of ndarrays for arguments to a function
    consistent with its signature with extra dimensions to test broadcasting.

    Parameters
    ----------
    signature : str
        Signature for shapes to be compatible with. Expects string in format
        of numpy generalized universal function signature, e.g.,
        `'(m,n),(n)->(m)'` for vectorized matrix-vector multiplication.
    excluded : list-like of integers
        Set of integers representing the positional for which the function will
        not be vectorized. Uses same format as `numpy.vectorize`.
    min_side : int
        Minimum size of any side of the arrays. It is good to test the corner
        cases of 0 or 1 sized dimensions when applicable, but if not, it a min
        size can be supplied here.
    max_side : int
        Maximum size of any side of the arrays. This can usually be kept small
        and still find most corner cases in testing.
    max_extra : int
        Maximum number of extra dimensions that can be appended on left of
        arrays for broadcasting. This should be kept small as the memory used
        grows exponentially with extra dimensions.

    Returns
    ----------
    shapes : list of tuples
        list of tuples where each tuple is the shape of an argument. Extra
        dimensions for broadcasting will be present in the shapes.

    See Also
    --------
    See `numpy.vectorize` at
    docs.scipy.org/doc/numpy-1.14.0/reference/generated/numpy.vectorize.html
    '''
    # Get core shapes before broadcasted dimensions
    # e.g., shapes = [(1, 3), (3, 1)]
    shapes = draw(gufunc_shape(signature,
                               min_side=min_side, max_side=max_side))

    # Which extra dims will just be 1 to get broadcasted, specified by mask
    n_extra = draw(integers(min_value=0, max_value=max_extra))  # e.g., 2
    # e.g., mask = [[True False], [False False]]
    mask = draw(arrays(np.bool, (len(shapes), n_extra)))

    # Build 2D array with extra dimensions
    extra_dim_gen = integers(min_value=min_side, max_value=max_side)
    # e.g., extra_dims = [2 5]
    extra_dims = draw(arrays(np.int, (n_extra,), elements=extra_dim_gen))
    # e.g., extra_dims = [[2 5], [2 5]]
    extra_dims = np.tile(extra_dims, (len(shapes), 1))
    # e.g., extra_dims = [[1 5], [2 5]]
    extra_dims[mask] = 1

    # How many extra dims on left to include for each argument (implicitly) 1
    # for each chopped dim. Cannot include any extra for excluded arguments.
    # e.g., n_extra_per_arg = [1, 2]
    n_extra_per_arg = [0 if nn in excluded else
                       draw(integers(min_value=0, max_value=n_extra))
                       for nn in xrange(len(shapes))]

    # Get full dimensions (core+extra), will chop some on left randomly
    # e.g., shapes = [(5, 1, 3), (2, 5, 3, 1)]
    shapes = [tuple(pp[len(pp) - nn:]) + ss
              for ss, pp, nn in zip(shapes, extra_dims, n_extra_per_arg)]
    return shapes


@composite
def gufunc_broadcast(draw, signature, filler=floats, excluded=(),
                     min_side=0, max_side=5, max_extra=2, **kwargs):
    '''Strategy to generate a tuple of ndarrays for arguments to a function
    consistent with its signature with extra dimensions to test broadcasting.

    Parameters
    ----------
    signature : str
        Signature for shapes to be compatible with. Expects string in format
        of numpy generalized universal function signature, e.g.,
        `'(m,n),(n)->(m)'` for vectorized matrix-vector multiplication.
    filler : strategy
        Strategy to fill in array elements e.g. `hypothesis.strategies.floats`.
        The parameters for `filler` are specified by the `kwargs`.
    excluded : list-like of integers
        Set of integers representing the positional for which the function will
        not be vectorized. Uses same format as `numpy.vectorize`.
    min_side : int
        Minimum size of any side of the arrays. It is good to test the corner
        cases of 0 or 1 sized dimensions when applicable, but if not, it a min
        size can be supplied here.
    max_side : int
        Maximum size of any side of the arrays. This can usually be kept small
        and still find most corner cases in testing.
    max_extra : int
        Maximum number of extra dimensions that can be appended on left of
        arrays for broadcasting. This should be kept small as the memory used
        grows exponentially with extra dimensions.

    Returns
    -------
    res : tuple of ndarrays
        Resulting ndarrays with shapes consistent with `signature` and elements
        from `filler`. Extra dimensions for broadcasting will be present.

    See Also
    --------
    See `numpy.vectorize` at
    docs.scipy.org/doc/numpy-1.14.0/reference/generated/numpy.vectorize.html
    '''
    shapes = draw(gufunc_broadcast_shape(signature, excluded=excluded,
                                         min_side=min_side, max_side=max_side,
                                         max_extra=max_extra))
    res = draw(tuple_of_arrays(shapes, filler, **kwargs))
    return res


def broadcasted(f, signature, otypes=None, excluded=(), **kwargs):
    '''Strategy that makes it easy to test the broadcasting semantics of a
    function against the 'ground-truth' broadcasting convention provided by
    `numpy.vectorize`.

    Extra parameters for `gufunc_broadcast` can be provided as `kwargs`.

    Parameters
    ----------
    f : callable
        This is the original function handles broadcasting itself.
    signature : str
        Signature for shapes to be compatible with. Expects string in format
        of numpy generalized universal function signature, e.g.,
        `'(m,n),(n)->(m)'` for vectorized matrix-vector multiplication.
    otypes : list of dtypes
        The dtypes for the the outputs of `f`. It must be a list with one dtype
        for each output argument of `f`. It must be a singleton list if `f`
        only returns a single output. It can also be set to `None` to leave it
        to be inferred, but this can create issues with empty arrays.
    excluded : list-like of integers
        Set of integers representing the positional for which the function will
        not be vectorized. Uses same format as `numpy.vectorize`.

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
    '''
    f_vec = np.vectorize(f, signature=signature, otypes=otypes)
    broadcasted_args = gufunc_broadcast(signature, excluded=excluded, **kwargs)
    funcs_and_args = tuples(just(f), just(f_vec), broadcasted_args)
    return funcs_and_args


@composite
def axised(draw, f, signature,
           filler=floats, min_side=0, max_side=5, max_extra=2, allow_none=True,
           **kwargs):
    '''Strategy that makes it easy to test the broadcasting semantics of a
    function against the 'ground-truth' broadcasting convention provided by
    `numpy.apply_along_axis`.

    Parameters
    ----------
    f : callable
        This is the original function with the form f(..., axis=None)
    signature : str
        Signature for shapes to be compatible with. Expects string in format
        of numpy generalized universal function signature. This does not
        include the axis kwarg. For testing axis, the core dimension of the
        first argument must be 1D. For, `np.mean` we use the signature
        `'(n)->()'` or for `'np.percentile'` we use `'(n),()->()'`.
    filler : strategy
        Strategy to fill in array elements e.g. `hypothesis.strategies.floats`.
        The parameters for `filler` are specified by the `kwargs`.
    min_side : int
        Minimum size of any side of the arrays. It is good to test the corner
        cases of 0 or 1 sized dimensions when applicable, but if not, it a min
        size can be supplied here.
    max_side : int
        Maximum size of any side of the arrays. This can usually be kept small
        and still find most corner cases in testing.
    max_extra : int
        Maximum number of extra dimensions that can be added to the first
        argument of `f`, which is the argument that `numpy.apply_along_axis`
        operates on. This should be kept small as the memory used
        grows exponentially with extra dimensions.
    allow_none : bool
        If True, sometimes creates test cases where the axis argument is None,
        which implies the first argument should be flattened before use.

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
    '''
    # This could be made argument as well if we like, np.apply_along_axis
    # doesn't like when this is 0, but we could handle that case ourselves.
    min_side = 1

    def f_axis(X, *args, **kwargs):
        axis = kwargs.get('axis', None)  # This trick is not needed in Python3

        if axis is None:
            Y = f(np.ravel(X), *args)
        else:
            Y = np.apply_along_axis(f, axis, X, *args)
        return Y

    side_base = integers(min_value=min_side, max_value=max_side)
    X_shape = draw(lists(side_base, min_size=1, max_size=max_extra + 1))
    axis = draw(integers(min_value=0, max_value=len(X_shape) - 1))

    shapes = draw(gufunc_shape(signature,
                               min_side=min_side, max_side=max_side))
    n, = shapes[0]  # must be singleton by spec
    X_shape[axis] = n
    shapes[0] = X_shape

    args = draw(tuple_of_arrays(shapes, filler, **kwargs))

    if allow_none and draw(booleans()):
        axis = None  # Sometimes we want to check this too

    funcs_and_args = (f, f_axis, args, axis)
    return funcs_and_args
