from __future__ import absolute_import

import string
import numpy as np
import numpy.lib.function_base as npfb
from hypothesis import given
from hypothesis.strategies import integers, lists, data, sampled_from, booleans
import hypothesis.extra.gufunc as gu
from hypothesis.extra.numpy import scalar_dtypes

# TODO consider if tuple_of_arrays should always return np.array
# TODO eliminate need for padding using gufuncs and filler, might need next API

# TODO check all comments and usages of min_side, max_side for bcast
# TODO max extra to max extra dims??
# TODO order_check etc
# Check going over full support of funcs

NP_BROADCASTABLE = ((np.matmul, '(n,m),(m,p)->(n,p)'),
                    (np.add, '(),()->()'),
                    (np.multiply, '(),()->()'))


# Also include if function can handle axis=None
NP_AXIS = ((np.sum, '(n)->()', True),
           (np.cumsum, '(n)->(n)', True),
           (np.percentile, '(n),()->()', True),
           (np.diff, '(n)->(m)', False),
           (np.diff, '(n),()->(m)', False))

SHAPE_VARS = string.digits + string.ascii_lowercase


def parsed_sigs(max_dims=3):
    '''Strategy to generate a parsed gufunc signature'''
    shapes = lists(sampled_from(SHAPE_VARS),
                   min_size=0, max_size=max_dims).map(tuple)
    S = lists(shapes, min_size=1, max_size=5)
    return S


def pad_left(L, size, padding):
    L = (padding,) * max(0, size - len(L)) + L
    return L


def unparse(parsed_sig):
    assert len(parsed_sig) > 0, 'gufunc sig does not support no argument funcs'

    sig = [','.join(vv) for vv in parsed_sig]
    sig = '(' + '),('.join(sig) + ')'
    return sig


def validate_shapes(L, parsed_sig, min_side, max_side):
    assert type(L) == list
    assert len(parsed_sig) == len(L)
    size_lookup = {}
    for spec, drawn in zip(parsed_sig, L):
        assert type(drawn) == tuple
        assert len(spec) == len(drawn)
        for ss, dd in zip(spec, drawn):
            # TODO adapt this in Py3, pull to subroutine
            assert type(dd) in (int, long)
            if ss.isdigit():
                assert int(ss) == dd
            else:
                assert min_side <= dd
                assert dd <= max_side
                var_size = size_lookup.setdefault(ss, dd)
                assert var_size == dd


def validate_elements(L):
    for drawn in L:
        # TODO after API change, can make bigger test of elements elsewhere
        assert np.asarray(drawn).dtype == int
        assert np.all(0 <= drawn)
        assert np.all(drawn <= 5)


def validate_bcast_shapes(shapes, parsed_sig, min_side, max_side, max_extra):
    # chop off extra dims then same as gufunc_shape
    core_dims = [tt[len(tt) - len(pp):] for tt, pp in zip(shapes, parsed_sig)]
    validate_shapes(core_dims, parsed_sig, min_side, max_side)

    # check max_extra
    b_dims = [tt[:len(tt) - len(pp)] for tt, pp in zip(shapes, parsed_sig)]
    assert all(len(tt) <= max_extra for tt in b_dims)

    # TODO use np built in bcast checkers

    # Convert dims to matrix form
    b_dims2 = np.array([pad_left(bb, max_extra, 1) for bb in b_dims],
                       dtype=int)
    # The extra broadcast dims be set to one regardless of min, max sides
    assert np.all((b_dims2 == 1) | (min_side <= b_dims2))
    assert np.all((b_dims2 == 1) | (b_dims2 <= max_side))
    # make sure 1 or same
    for ii in range(max_extra):
        vals = set(b_dims2[:, ii])
        # Must all be 1 or a const size
        assert len(vals) <= 2
        assert len(vals) < 2 or (1 in vals)


# hypothesis.extra.numpy.array_shapes does not support 0 min_size so we roll
# our own in this case.
@given(lists(lists(integers(min_value=0, max_value=5),
                   min_size=0, max_size=3), min_size=0, max_size=5), data())
def test_shapes_tuple_of_arrays(shapes, data):
    S = gu.tuple_of_arrays(shapes, integers, min_value=0, max_value=5)
    X = data.draw(S)

    validate_elements(X)

    assert len(shapes) == len(X)
    for spec, drawn in zip(shapes, X):
        assert tuple(spec) == np.shape(drawn)


@given(parsed_sigs())
def test_unparse_parse(parsed_sig):
    # We don't care about the output for this function
    signature = unparse(parsed_sig) + '->()'
    # This is a 'private' function of np, so need to test it still works as we
    # think it does.
    inp, _ = npfb._parse_gufunc_signature(signature)

    assert parsed_sig == inp


@given(parsed_sigs(), integers(0, 100), integers(0, 100), data())
def test_constraints_gufunc_shape(parsed_sig, min_side, max_side, data):
    # We don't care about the output for this function
    signature = unparse(parsed_sig) + '->()'

    min_side, max_side = sorted([min_side, max_side])

    S = gu.gufunc_shape(signature, min_side=min_side, max_side=max_side)

    shapes = data.draw(S)
    validate_shapes(shapes, parsed_sig, min_side, max_side)


@given(parsed_sigs(), integers(0, 5), integers(0, 5), data())
def test_constraints_gufunc(parsed_sig, min_side, max_side, data):
    # We don't care about the output for this function
    signature = unparse(parsed_sig) + '->()'

    min_side, max_side = sorted([min_side, max_side])

    S = gu.gufunc(signature, filler=integers,
                  min_side=min_side, max_side=max_side,
                  min_value=0, max_value=5)

    X = data.draw(S)
    shapes = [np.shape(xx) for xx in X]

    validate_shapes(shapes, parsed_sig, min_side, max_side)
    validate_elements(X)


@given(parsed_sigs(max_dims=3), lists(booleans(), min_size=3, max_size=3),
       integers(0, 100), integers(0, 100), integers(0, 5), data())
def test_bcast_gufunc_broadcast_shape(parsed_sig, excluded, min_side, max_side,
                                      max_extra, data):
    # We don't care about the output for this function
    signature = unparse(parsed_sig) + '->()'

    excluded = excluded[:len(parsed_sig)]
    excluded, = np.where(excluded)
    excluded = tuple(excluded)

    min_side, max_side = sorted([min_side, max_side])

    S = gu.gufunc_broadcast_shape(signature, excluded=excluded,
                                  min_side=min_side, max_side=max_side,
                                  max_extra=max_extra)

    shapes = data.draw(S)

    validate_bcast_shapes(shapes, parsed_sig, min_side, max_side, max_extra)


@given(parsed_sigs(max_dims=3), lists(booleans(), min_size=3, max_size=3),
       integers(0, 5), integers(0, 5), integers(0, 3), data())
def test_bcast_gufunc_broadcast(parsed_sig, excluded, min_side, max_side,
                                max_extra, data):
    # We don't care about the output for this function
    signature = unparse(parsed_sig) + '->()'

    excluded = excluded[:len(parsed_sig)]
    excluded, = np.where(excluded)
    excluded = tuple(excluded)

    min_side, max_side = sorted([min_side, max_side])

    S = gu.gufunc_broadcast(signature, filler=integers, excluded=excluded,
                            min_side=min_side, max_side=max_side,
                            max_extra=max_extra, min_value=0, max_value=5)

    X = data.draw(S)
    shapes = [np.shape(xx) for xx in X]

    validate_bcast_shapes(shapes, parsed_sig, min_side, max_side, max_extra)
    validate_elements(X)


@given(parsed_sigs(max_dims=3), parsed_sigs(max_dims=3),
       lists(scalar_dtypes(), min_size=3, max_size=3),
       lists(booleans(), min_size=3, max_size=3),
       integers(0, 5), integers(0, 5), integers(0, 3), data())
def test_bcast_broadcasted(parsed_sig, o_parsed_sig, otypes, excluded,
                           min_side, max_side, max_extra, data):
    signature = unparse(parsed_sig) + '->' + unparse(o_parsed_sig)

    # These are of type np.dtype, but we test use str elsewhere
    otypes = otypes[:len(parsed_sig)]

    excluded = excluded[:len(parsed_sig)]
    excluded, = np.where(excluded)
    excluded = tuple(excluded)

    min_side, max_side = sorted([min_side, max_side])

    def dummy(*args):
        assert False, 'this function shouldnt get called'

    S = gu.broadcasted(dummy, signature, otypes=otypes, excluded=excluded,
                       min_side=min_side, max_side=max_side,
                       max_extra=max_extra,
                       filler=integers, min_value=0, max_value=5)

    f0, f_vec, X = data.draw(S)

    # First argument is pass thru
    assert f0 is dummy
    assert id(f0) == id(dummy)

    # Second is result of np.vectorize, which we test elsewhere

    # Third same as gufunc_broadcast
    shapes = [np.shape(xx) for xx in X]
    validate_bcast_shapes(shapes, parsed_sig, min_side, max_side, max_extra)
    validate_elements(X)


@given(integers(0, len(NP_BROADCASTABLE) - 1),
       integers(0, 5), integers(0, 5), integers(0, 3), data())
def test_np_passes_broadcasted(func_choice, min_side, max_side, max_extra,
                               data):
    otype = 'int64'

    f, signature = NP_BROADCASTABLE[func_choice]

    min_side, max_side = sorted([min_side, max_side])

    S = gu.broadcasted(f, signature, otypes=[otype],
                       min_side=min_side, max_side=max_side,
                       max_extra=max_extra,
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
def test_multi_broadcasted(min_side, max_side, max_extra, data):
    min_side, max_side = sorted([min_side, max_side])

    def multi_out_f(x, y, q):
        '''Function should already be fully broadcast compatible.'''
        z = np.matmul(x, y)
        R = (z, z + 0.5 * q)
        return R

    signature = '(n,m),(m,p),()->(n,p),(n,p)'
    otypes = ['int64', 'float64']

    S = gu.broadcasted(multi_out_f, signature, otypes=otypes, excluded=(2,),
                       min_side=min_side, max_side=max_side,
                       max_extra=max_extra,
                       filler=integers, min_value=0, max_value=100)

    f0, f_vec, args = data.draw(S)

    assert f0 is multi_out_f
    assert np.shape(args[2]) == (), 'argument should be excluded from bcast'

    R1 = f0(*args)
    R2 = f_vec(*args)

    print 'args', args
    print 'f0', R1
    print 'fvec', R2

    for rr1, rr2, ot in zip(R1, R2, otypes):
        assert rr1.dtype == ot
        assert rr2.dtype == ot
        assert np.shape(rr1) == np.shape(rr2)
        assert np.all(rr1 == rr2)


@given(parsed_sigs(),
       integers(1, 5), integers(1, 5), integers(0, 3), booleans(), data())
def test_constraints_axised(parsed_sig, min_side, max_side, max_extra,
                            allow_none, data):
    # First argument must be 1D
    parsed_sig[0] = pad_left(parsed_sig[0], 1, 'n')[:1]
    signature = unparse(parsed_sig) + '->()'  # output dims ignored here

    min_side, max_side = sorted([min_side, max_side])

    def dummy(*args, **kwargs):
        assert False, 'this function shouldnt get called'

    S = gu.axised(dummy, signature, min_side=min_side, max_side=max_side,
                  max_extra=max_extra, allow_none=allow_none,
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


@given(integers(0, len(NP_AXIS) - 1),
       integers(1, 5), integers(1, 5), integers(0, 3), data())
def test_np_passes_axised(func_choice, min_side, max_side, max_extra, data):
    f, signature, allow_none = NP_AXIS[func_choice]

    min_side, max_side = sorted([min_side, max_side])

    S = gu.axised(f, signature, min_side=min_side, max_side=max_side,
                  max_extra=max_extra, allow_none=allow_none,
                  filler=integers, min_value=0, max_value=100)

    f0, f_ax, args, axis = data.draw(S)

    assert f0 is f

    R1 = f0(*args, axis=axis)
    R2 = f_ax(*args, axis=axis)
    assert R1.dtype == R2.dtype
    assert np.shape(R1) == np.shape(R2)
    assert np.all(R1 == R2)
