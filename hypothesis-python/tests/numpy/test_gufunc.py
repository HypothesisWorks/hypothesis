from __future__ import absolute_import

import string
import numpy as np
from hypothesis import given
from hypothesis.strategies import integers, lists, data, sampled_from
import hypothesis.extra.gufunc as gu
# from hypothesis.extra.numpy import scalar_dtypes, from_dtype

# TODO consider if tuple_of_arrays should always return np.array
# TODO note numpy>=1.12.0 for the sig parsing

SHAPE_VARS = string.digits + string.ascii_lowercase


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
            # TODO adapt this in Py3
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
             min_size=1, max_size=5), integers(0, 100), integers(0, 100),
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


def test_bcast_gufunc_broadcast_shape():
    # chop off extra dims then same as gufunc_shape
    # make sure compatible with broadcast_arrays
    # compute extra dims matrix: make sure 1 or same
    #    make sure extra in [min, max] side and under max extra
    #    also compute not always same??
    #    keep drawing until diff??
    # nothing extra if in excluded
    pass


def test_bcast_gufunc_broadcast():
    # same as gufunc_broadcast_shape but now use .shape
    pass


def test_elements_gufunc_broadcast():
    # again prob just a wrapper
    pass


def test_bcast_broadcasted():
    # take args and test same as gufunc_broadcast
    pass


def test_elements_broadcasted():
    # again prob just a wrapper
    pass


def test_first_arg_broadcasted():
    # test id just pass thru on first arg
    pass


def test_np_passes_broadcasted():
    # check function matches for built-in nps we know broadcast correct
    #    do with real sig
    #    then also do elementwise funcs and test arbitrary sigs??
    #    also test otypes match
    pass


def test_constraints_axised():
    # take args and test same as gufunc_broadcast
    pass


def test_elements_axised():
    # again prob just a wrapper
    pass


def test_first_arg_axised():
    # test id just pass thru on first arg
    pass


def test_np_passes_axised():
    # check function matches for built-in nps we know broadcast correct
    #    do with real sig
    pass


def test_none_arg_axised():
    # check never None is allow_none is false
    pass
