from __future__ import absolute_import, division, print_function

import string
# Note: this requires adding `future` to the test requirements!
from builtins import int as py3int

import numpy as np
import numpy.lib.function_base as npfb

import hypothesis.extra.gufunc as gu
from hypothesis import given
from hypothesis.extra.numpy import from_dtype, scalar_dtypes
from hypothesis.strategies import (
    booleans,
    data,
    from_regex,
    integers,
    lists,
    sampled_from,
)

NP_BROADCASTABLE = ((np.matmul, "(n,m),(m,p)->(n,p)"),
                    (np.add, "(),()->()"),
                    (np.multiply, "(),()->()"))


# Also include if function can handle axis=None
NP_AXIS = ((np.sum, "(n)->()", True),
           (np.cumsum, "(n)->(n)", True),
           (np.percentile, "(n),()->()", True),
           (np.diff, "(n)->(m)", False),
           (np.diff, "(n),()->(m)", False))

# The spec for a dimension name in numpy.lib.function_base, if we are happy
# testing single char var names we can switch this to '\A\w\Z' and save ~0.5s
# when running the tests. Officially, we should use r'\A\w+\Z' but this creates
# too many weird corner cases on Python3 unicode.
VALID_DIM_NAMES = r"\A[a-zA-Z_][a-zA-Z0-9_]*\Z"


def parsed_sigs(max_dims=3, max_args=5):
    """Strategy to generate a parsed gufunc signature.

    Note that in general functions can take no-args, but the function signature
    formalism is for >= 1 args. So, there is always at least 1 arg here.
    """
    # Use | to sample from digits since we would like pure numbers more often
    shapes = lists(from_regex(VALID_DIM_NAMES) | sampled_from(string.digits),
                   min_size=0, max_size=max_dims).map(tuple)
    S = lists(shapes, min_size=1, max_size=max_args)
    return S


def pad_left(L, size, padding):
    L = (padding,) * max(0, size - len(L)) + L
    return L


def unparse(parsed_sig):
    assert len(parsed_sig) > 0, "gufunc sig does not support no argument funcs"

    sig = [",".join(vv) for vv in parsed_sig]
    sig = "(" + "),(".join(sig) + ")"
    return sig


def check_int(x):
    """Use subroutine for this so in Py3 we can remove the `long`."""
    # Could also do ``type(x) in (int, long)``, but only on Py2.
    assert isinstance(x, py3int)


def validate_shapes(L, parsed_sig, min_side, max_side):
    assert type(L) == list
    assert len(parsed_sig) == len(L)
    size_lookup = {}
    for spec, drawn in zip(parsed_sig, L):
        assert type(drawn) == tuple
        assert len(spec) == len(drawn)
        for ss, dd in zip(spec, drawn):
            check_int(dd)
            if ss.isdigit():
                assert int(ss) == dd
            else:
                assert min_side <= dd
                assert dd <= max_side
                var_size = size_lookup.setdefault(ss, dd)
                assert var_size == dd


def validate_elements(L, elements=None):
    for drawn in L:
        drawn = np.asarray(drawn)
        if elements is None:  # Test int filler
            assert drawn.dtype == int
            assert np.all(0 <= drawn)
            assert np.all(drawn <= 5)
        else:
            elements = np.asarray(elements)
            assert drawn.dtype == elements.dtype
            vals = set(drawn.ravel())
            assert vals.issubset(elements)


def validate_bcast_shapes(shapes, parsed_sig,
                          min_side, max_side, max_dims_extra):
    assert all(len(ss) <= gu.GLOBAL_DIMS_MAX for ss in shapes)

    # chop off extra dims then same as gufunc_shape
    core_dims = [tt[len(tt) - len(pp):] for tt, pp in zip(shapes, parsed_sig)]
    validate_shapes(core_dims, parsed_sig, min_side, max_side)

    # check max_dims_extra
    b_dims = [tt[:len(tt) - len(pp)] for tt, pp in zip(shapes, parsed_sig)]
    assert all(len(tt) <= max_dims_extra for tt in b_dims)

    # Convert dims to matrix form
    b_dims2 = np.array([pad_left(bb, max_dims_extra, 1) for bb in b_dims],
                       dtype=int)
    # The extra broadcast dims be set to one regardless of min, max sides
    assert np.all((b_dims2 == 1) | (min_side <= b_dims2))
    assert np.all((b_dims2 == 1) | (b_dims2 <= max_side))
    # make sure 1 or same
    for ii in range(max_dims_extra):
        vals = set(b_dims2[:, ii])
        # Must all be 1 or a const size
        assert len(vals) <= 2
        assert len(vals) < 2 or (1 in vals)


@given(scalar_dtypes(),
       lists(integers(min_value=0, max_value=5),
             min_size=0, max_size=3).map(tuple), booleans(), data())
def test_arrays_(dtype, shape, force_ndarray, data):
    elements = data.draw(lists(from_dtype(dtype), min_size=1, max_size=10))
    # testing elements equality tricky with nans
    elements = np.nan_to_num(elements)
    elements_st = sampled_from(elements)

    S = gu.arrays_(elements.dtype, shape, elements_st,
                   force_ndarray=force_ndarray)
    X = data.draw(S)

    assert np.shape(X) == shape
    validate_elements([X], elements=elements)

    if force_ndarray or np.size(X) != 1:
        assert type(X) == np.ndarray


# hypothesis.extra.numpy.array_shapes does not support 0 min_size so we roll
# our own in this case.
@given(lists(lists(integers(min_value=0, max_value=5),
                   min_size=0, max_size=3).map(tuple),
             min_size=0, max_size=5), data())
def test_shapes_tuple_of_arrays(shapes, data):
    S = gu.tuple_of_arrays(shapes, integers, min_value=0, max_value=5)
    X = data.draw(S)

    validate_elements(X)

    assert len(shapes) == len(X)
    for spec, drawn in zip(shapes, X):
        assert tuple(spec) == np.shape(drawn)


@given(lists(lists(integers(min_value=0, max_value=5),
                   min_size=0, max_size=3).map(tuple),
             min_size=0, max_size=5), scalar_dtypes(), data())
def test_elements_tuple_of_arrays(shapes, dtype, data):
    elements = data.draw(lists(from_dtype(dtype), min_size=1, max_size=10))
    # testing elements equality tricky with nans
    elements = np.nan_to_num(elements)

    S = gu.tuple_of_arrays(shapes, sampled_from, elements=elements)
    X = data.draw(S)

    validate_elements(X, elements=elements)


@given(parsed_sigs(), parsed_sigs())
def test_unparse_parse(i_parsed_sig, o_parsed_sig):
    # We don't care about the output for this function
    signature = unparse(i_parsed_sig) + "->" + unparse(o_parsed_sig)
    # This is a 'private' function of np, so need to test it still works as we
    # think it does.
    inp, out = npfb._parse_gufunc_signature(signature)

    assert i_parsed_sig == inp
    assert o_parsed_sig == out


@given(parsed_sigs(), integers(0, 100), integers(0, 100), data())
def test_shapes_gufunc_shape(parsed_sig, min_side, max_side, data):
    # We don't care about the output for this function
    signature = unparse(parsed_sig) + "->()"

    min_side, max_side = sorted([min_side, max_side])

    S = gu.gufunc_shape(signature, min_side=min_side, max_side=max_side)

    shapes = data.draw(S)
    validate_shapes(shapes, parsed_sig, min_side, max_side)


@given(parsed_sigs(), integers(0, 5), integers(0, 5), data())
def test_shapes_gufunc(parsed_sig, min_side, max_side, data):
    # We don't care about the output for this function
    signature = unparse(parsed_sig) + "->()"

    min_side, max_side = sorted([min_side, max_side])

    S = gu.gufunc(signature, filler=integers,
                  min_side=min_side, max_side=max_side,
                  min_value=0, max_value=5)

    X = data.draw(S)
    shapes = [np.shape(xx) for xx in X]

    validate_shapes(shapes, parsed_sig, min_side, max_side)
    validate_elements(X)


@given(parsed_sigs(max_args=3), integers(0, 5), integers(0, 5),
       scalar_dtypes(), data())
def test_elements_gufunc(parsed_sig, min_side, max_side, dtype, data):
    elements = data.draw(lists(from_dtype(dtype), min_size=1, max_size=10))
    # testing elements equality tricky with nans
    elements = np.nan_to_num(elements)

    # We don't care about the output for this function
    signature = unparse(parsed_sig) + "->()"

    min_side, max_side = sorted([min_side, max_side])

    S = gu.gufunc(signature, filler=sampled_from,
                  min_side=min_side, max_side=max_side, elements=elements)

    X = data.draw(S)

    validate_elements(X, elements=elements)


@given(parsed_sigs(max_args=10, max_dims=gu.GLOBAL_DIMS_MAX),
       lists(booleans(), min_size=10, max_size=10),
       integers(0, 100), integers(0, 100), integers(0, gu.GLOBAL_DIMS_MAX),
       data())
def test_shapes_gufunc_broadcast_shape(parsed_sig, excluded,
                                       min_side, max_side, max_dims_extra,
                                       data):
    # We don't care about the output for this function
    signature = unparse(parsed_sig) + "->()"

    excluded = excluded[:len(parsed_sig)]
    assert len(excluded) == len(parsed_sig)  # Make sure excluded long enough
    excluded, = np.where(excluded)
    excluded = tuple(excluded)

    min_side, max_side = sorted([min_side, max_side])

    S = gu.gufunc_broadcast_shape(signature, excluded=excluded,
                                  min_side=min_side, max_side=max_side,
                                  max_dims_extra=max_dims_extra)

    shapes = data.draw(S)

    validate_bcast_shapes(shapes, parsed_sig,
                          min_side, max_side, max_dims_extra)


@given(parsed_sigs(max_args=3), lists(booleans(), min_size=3, max_size=3),
       integers(0, 5), integers(0, 5), integers(0, 3), data())
def test_shapes_gufunc_broadcast(parsed_sig, excluded, min_side, max_side,
                                 max_dims_extra, data):
    # We don't care about the output for this function
    signature = unparse(parsed_sig) + "->()"

    excluded = excluded[:len(parsed_sig)]
    assert len(excluded) == len(parsed_sig)  # Make sure excluded long enough
    excluded, = np.where(excluded)
    excluded = tuple(excluded)

    min_side, max_side = sorted([min_side, max_side])

    S = gu.gufunc_broadcast(signature, filler=integers, excluded=excluded,
                            min_side=min_side, max_side=max_side,
                            max_dims_extra=max_dims_extra,
                            min_value=0, max_value=5)

    X = data.draw(S)
    shapes = [np.shape(xx) for xx in X]

    validate_bcast_shapes(shapes, parsed_sig,
                          min_side, max_side, max_dims_extra)
    validate_elements(X)


@given(parsed_sigs(max_args=3), lists(booleans(), min_size=3, max_size=3),
       integers(0, 5), integers(0, 5), integers(0, 3), scalar_dtypes(), data())
def test_elements_gufunc_broadcast(parsed_sig, excluded, min_side, max_side,
                                   max_dims_extra, dtype, data):
    # We don't care about the output for this function
    signature = unparse(parsed_sig) + "->()"

    excluded = excluded[:len(parsed_sig)]
    assert len(excluded) == len(parsed_sig)  # Make sure excluded long enough
    excluded, = np.where(excluded)
    excluded = tuple(excluded)

    min_side, max_side = sorted([min_side, max_side])

    elements = data.draw(lists(from_dtype(dtype), min_size=1, max_size=10))
    # testing elements equality tricky with nans
    elements = np.nan_to_num(elements)

    S = gu.gufunc_broadcast(signature, filler=sampled_from, excluded=excluded,
                            min_side=min_side, max_side=max_side,
                            max_dims_extra=max_dims_extra, elements=elements)

    X = data.draw(S)

    validate_elements(X, elements=elements)


@given(parsed_sigs(max_args=3), parsed_sigs(),
       lists(scalar_dtypes(), min_size=3, max_size=3),
       lists(booleans(), min_size=3, max_size=3),
       integers(0, 5), integers(0, 5), integers(0, 3), data())
def test_shapes_broadcasted(parsed_sig, o_parsed_sig, otypes, excluded,
                            min_side, max_side, max_dims_extra, data):
    signature = unparse(parsed_sig) + "->" + unparse(o_parsed_sig)

    # These are of type np.dtype, but we test use str elsewhere
    otypes = otypes[:len(parsed_sig)]
    assert len(otypes) == len(parsed_sig)  # Make sure otypes long enough

    excluded = excluded[:len(parsed_sig)]
    assert len(excluded) == len(parsed_sig)  # Make sure excluded long enough
    excluded, = np.where(excluded)
    excluded = tuple(excluded)

    min_side, max_side = sorted([min_side, max_side])

    def dummy(*args):
        assert False, "this function shouldnt get called"

    S = gu.broadcasted(dummy, signature, otypes=otypes, excluded=excluded,
                       min_side=min_side, max_side=max_side,
                       max_dims_extra=max_dims_extra,
                       filler=integers, min_value=0, max_value=5)

    f0, f_vec, X = data.draw(S)

    # First argument is pass thru
    assert f0 is dummy
    assert id(f0) == id(dummy)

    # Second is result of np.vectorize, which we test elsewhere

    # Third same as gufunc_broadcast
    shapes = [np.shape(xx) for xx in X]
    validate_bcast_shapes(shapes, parsed_sig,
                          min_side, max_side, max_dims_extra)
    validate_elements(X)


@given(parsed_sigs(max_args=3), parsed_sigs(),
       lists(scalar_dtypes(), min_size=3, max_size=3),
       lists(booleans(), min_size=3, max_size=3),
       integers(0, 5), integers(0, 5), integers(0, 3), scalar_dtypes(), data())
def test_elements_broadcasted(parsed_sig, o_parsed_sig, otypes, excluded,
                              min_side, max_side, max_dims_extra, dtype, data):
    signature = unparse(parsed_sig) + "->" + unparse(o_parsed_sig)

    # These are of type np.dtype, but we test use str elsewhere
    otypes = otypes[:len(parsed_sig)]
    assert len(otypes) == len(parsed_sig)  # Make sure otypes long enough

    excluded = excluded[:len(parsed_sig)]
    assert len(excluded) == len(parsed_sig)  # Make sure excluded long enough
    excluded, = np.where(excluded)
    excluded = tuple(excluded)

    min_side, max_side = sorted([min_side, max_side])

    def dummy(*args):
        assert False, "this function shouldnt get called"

    elements = data.draw(lists(from_dtype(dtype), min_size=1, max_size=10))
    # testing elements equality tricky with nans
    elements = np.nan_to_num(elements)

    S = gu.broadcasted(dummy, signature, otypes=otypes, excluded=excluded,
                       min_side=min_side, max_side=max_side,
                       max_dims_extra=max_dims_extra,
                       filler=sampled_from, elements=elements)

    f0, f_vec, X = data.draw(S)

    validate_elements(X, elements=elements)


@given(integers(0, len(NP_BROADCASTABLE) - 1),
       integers(0, 5), integers(0, 5), integers(0, 3), data())
def test_np_broadcasted(func_choice, min_side, max_side, max_dims_extra, data):
    otype = "int64"

    f, signature = NP_BROADCASTABLE[func_choice]

    min_side, max_side = sorted([min_side, max_side])

    S = gu.broadcasted(f, signature, otypes=[otype],
                       min_side=min_side, max_side=max_side,
                       max_dims_extra=max_dims_extra,
                       filler=integers, min_value=0, max_value=100)

    f0, f_vec, args = data.draw(S)

    assert f0 is f

    R1 = f0(*args)
    R2 = f_vec(*args)
    assert R1.dtype == otype
    assert R2.dtype == otype
    assert np.shape(R1) == np.shape(R2)
    assert np.all(R1 == R2)  # All int so no round off error


@given(integers(0, 5), integers(0, 5), integers(0, 3), data())
def test_np_multi_broadcasted(min_side, max_side, max_dims_extra, data):
    min_side, max_side = sorted([min_side, max_side])

    def multi_out_f(x, y, q):
        """Function should already be fully broadcast compatible."""
        z = np.matmul(x, y)
        R = (z, z + 0.5 * q)
        return R

    signature = "(n,m),(m,p),()->(n,p),(n,p)"
    otypes = ["int64", "float64"]

    S = gu.broadcasted(multi_out_f, signature, otypes=otypes, excluded=(2,),
                       min_side=min_side, max_side=max_side,
                       max_dims_extra=max_dims_extra,
                       filler=integers, min_value=0, max_value=100)

    f0, f_vec, args = data.draw(S)

    assert f0 is multi_out_f
    assert np.shape(args[2]) == (), "argument should be excluded from bcast"

    R1 = f0(*args)
    R2 = f_vec(*args)

    for rr1, rr2, ot in zip(R1, R2, otypes):
        assert rr1.dtype == ot
        assert rr2.dtype == ot
        assert np.shape(rr1) == np.shape(rr2)
        assert np.all(rr1 == rr2)


@given(parsed_sigs(),
       integers(1, 5), integers(1, 5), integers(0, 3), booleans(), data())
def test_shapes_axised(parsed_sig, min_side, max_side, max_dims_extra,
                       allow_none, data):
    # First argument must be 1D
    parsed_sig[0] = pad_left(parsed_sig[0], 1, "n")[:1]
    signature = unparse(parsed_sig) + "->()"  # output dims ignored here

    min_side, max_side = sorted([min_side, max_side])

    def dummy(*args, **kwargs):
        assert False, "this function shouldnt get called"

    S = gu.axised(dummy, signature, min_side=min_side, max_side=max_side,
                  max_dims_extra=max_dims_extra, allow_none=allow_none,
                  filler=integers, min_value=0, max_value=5)

    f0, f_ax, X, axis = data.draw(S)

    # First argument is pass thru
    assert f0 is dummy
    assert id(f0) == id(dummy)

    # Second is result of np.vectorize, which we test elsewhere

    # Third same as gufunc_broadcast
    shapes = [np.shape(xx) for xx in X]
    if axis is None:
        # First arg shape can be arbitrary with axis=None
        assert len(shapes[0]) >= 1
        validate_shapes(shapes[1:], parsed_sig[1:], min_side, max_side)
    else:
        shapes[0] = (X[0].shape[axis],)
        validate_shapes(shapes, parsed_sig, min_side, max_side)

    validate_elements(X)

    # Test fourth
    assert allow_none or (axis is not None)


@given(parsed_sigs(), integers(1, 5), integers(1, 5), integers(0, 3),
       booleans(), scalar_dtypes(), data())
def test_elements_axised(parsed_sig, min_side, max_side, max_dims_extra,
                         allow_none, dtype, data):
    # First argument must be 1D
    parsed_sig[0] = pad_left(parsed_sig[0], 1, "n")[:1]
    signature = unparse(parsed_sig) + "->()"  # output dims ignored here

    min_side, max_side = sorted([min_side, max_side])

    def dummy(*args, **kwargs):
        assert False, "this function shouldnt get called"

    elements = data.draw(lists(from_dtype(dtype), min_size=1, max_size=10))
    # testing elements equality tricky with nans
    elements = np.nan_to_num(elements)

    S = gu.axised(dummy, signature, min_side=min_side, max_side=max_side,
                  max_dims_extra=max_dims_extra, allow_none=allow_none,
                  filler=sampled_from, elements=elements)

    f0, f_ax, X, axis = data.draw(S)

    validate_elements(X, elements=elements)


@given(integers(0, len(NP_AXIS) - 1),
       integers(1, 5), integers(1, 5), integers(0, 3), data())
def test_np_axised(func_choice, min_side, max_side, max_dims_extra, data):
    f, signature, allow_none = NP_AXIS[func_choice]

    min_side, max_side = sorted([min_side, max_side])

    S = gu.axised(f, signature, min_side=min_side, max_side=max_side,
                  max_dims_extra=max_dims_extra, allow_none=allow_none,
                  filler=integers, min_value=0, max_value=100)

    f0, f_ax, args, axis = data.draw(S)

    assert f0 is f

    R1 = f0(*args, axis=axis)
    R2 = f_ax(*args, axis=axis)
    assert R1.dtype == R2.dtype
    assert np.shape(R1) == np.shape(R2)
    assert np.all(R1 == R2)
