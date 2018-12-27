from __future__ import absolute_import

import string
import numpy as np
from hypothesis import given
from hypothesis.strategies import integers, lists, data, sampled_from, booleans
import hypothesis.extra.gufunc as gu
from hypothesis.extra.numpy import scalar_dtypes

# TODO consider if tuple_of_arrays should always return np.array
# TODO note numpy>=1.12.0 for the sig parsing
# TODO check all comments and usages of min_side, max_side for bcast
# TODO move order of sig preproc
# TODO make function for repeated strats
# TODO eliminate need for padding using gufuncs and filler, might need next API

#                    (np.percentile, '(n),()->()')

NP_BROADCASTABLE = ((np.matmul, '(n,m),(m,p)->(n,p)'),
                    (np.add, '(),()->()'),
                    (np.multiply, '(),()->()'))

SHAPE_VARS = string.digits + string.ascii_lowercase


def pad_left(L, size, padding):
    L = [padding] * max(0, size - len(L)) + L
    return L


def unparse(parsed_sig):
    # TODO explain [] not valid here
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
    b_dims2 = np.array([pad_left(list(bb), max_extra, 1) for bb in b_dims],
                       dtype=int)
    # TODO comment
    assert np.all((b_dims2 == 1) | (min_side <= b_dims2))
    assert np.all((b_dims2 == 1) | (b_dims2 <= max_side))
    # make sure 1 or same
    for ii in range(max_extra):
        vals = set(b_dims2[:, ii])
        # Must all be 1 or a const size
        assert len(vals) <= 2
        assert len(vals) < 2 or (1 in vals)


@given(lists(lists(integers(min_value=0, max_value=5),
                   min_size=0, max_size=3), min_size=0, max_size=5), data())
def test_shapes_tuple_of_arrays(shapes, data):
    S = gu.tuple_of_arrays(shapes, integers, min_value=0, max_value=5)
    X = data.draw(S)

    validate_elements(X)

    assert len(shapes) == len(X)
    for spec, drawn in zip(shapes, X):
        assert tuple(spec) == np.shape(drawn)


@given(lists(lists(sampled_from(SHAPE_VARS), min_size=0, max_size=3),
             min_size=1, max_size=5), integers(0, 100), integers(0, 100),
       data())
def test_constraints_gufunc_shape(parsed_sig, min_side, max_side, data):
    min_side, max_side = sorted([min_side, max_side])

    # We don't care about the output for this function
    signature = unparse(parsed_sig) + '->()'

    S = gu.gufunc_shape(signature, min_side=min_side, max_side=max_side)

    shapes = data.draw(S)
    validate_shapes(shapes, parsed_sig, min_side, max_side)


@given(lists(lists(sampled_from(SHAPE_VARS), min_size=0, max_size=3),
             min_size=1, max_size=5), integers(0, 5), integers(0, 5),
       data())
def test_constraints_gufunc(parsed_sig, min_side, max_side, data):
    min_side, max_side = sorted([min_side, max_side])

    # We don't care about the output for this function
    signature = unparse(parsed_sig) + '->()'

    S = gu.gufunc(signature, filler=integers,
                  min_side=min_side, max_side=max_side,
                  min_value=0, max_value=5)

    X = data.draw(S)
    shapes = [np.shape(xx) for xx in X]

    validate_shapes(shapes, parsed_sig, min_side, max_side)
    validate_elements(X)


@given(lists(lists(sampled_from(SHAPE_VARS), min_size=0, max_size=3),
             min_size=1, max_size=5),
       lists(booleans(), min_size=3, max_size=3),
       integers(0, 100), integers(0, 100), integers(0, 5), data())
def test_bcast_gufunc_broadcast_shape(parsed_sig, excluded, min_side, max_side,
                                      max_extra, data):
    excluded = excluded[:len(parsed_sig)]
    excluded, = np.where(excluded)
    excluded = tuple(excluded)

    min_side, max_side = sorted([min_side, max_side])

    # We don't care about the output for this function
    signature = unparse(parsed_sig) + '->()'

    S = gu.gufunc_broadcast_shape(signature, excluded=excluded,
                                  min_side=min_side, max_side=max_side,
                                  max_extra=max_extra)

    shapes = data.draw(S)

    validate_bcast_shapes(shapes, parsed_sig, min_side, max_side, max_extra)


@given(lists(lists(sampled_from(SHAPE_VARS), min_size=0, max_size=3),
             min_size=1, max_size=5),
       lists(booleans(), min_size=3, max_size=3),
       integers(0, 5), integers(0, 5), integers(0, 3), data())
def test_bcast_gufunc_broadcast(parsed_sig, excluded, min_side, max_side,
                                max_extra, data):
    excluded = excluded[:len(parsed_sig)]
    excluded, = np.where(excluded)
    excluded = tuple(excluded)

    min_side, max_side = sorted([min_side, max_side])

    # We don't care about the output for this function
    signature = unparse(parsed_sig) + '->()'

    S = gu.gufunc_broadcast(signature, filler=integers, excluded=excluded,
                            min_side=min_side, max_side=max_side,
                            max_extra=max_extra, min_value=0, max_value=5)

    X = data.draw(S)
    shapes = [np.shape(xx) for xx in X]

    validate_bcast_shapes(shapes, parsed_sig, min_side, max_side, max_extra)
    validate_elements(X)


@given(lists(lists(sampled_from(SHAPE_VARS), min_size=0, max_size=3),
             min_size=1, max_size=5),
       lists(scalar_dtypes(), min_size=3, max_size=3),
       lists(booleans(), min_size=3, max_size=3),
       integers(0, 5), integers(0, 5), integers(0, 3), data())
def test_bcast_broadcasted(parsed_sig, otypes, excluded, min_side, max_side,
                           max_extra, data):
    # TODO also put random output sig as well
    signature = unparse(parsed_sig) + '->()'

    # TODO also test taking None sometimes, or these are str or type
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

    R1 = f0(*args)
    R2 = f_vec(*args)
    assert(R1.dtype == otype)
    assert(R2.dtype == otype)
    assert(np.all(R1 == R2))  # All int so no round off error


def test_constraints_axised():
    # take args and test same as gufunc_broadcast
    pass


def test_np_passes_axised():
    # check function matches for built-in nps we know broadcast correct
    #    do with real sig
    pass


def test_none_arg_axised():
    # check never None is allow_none is false
    pass
