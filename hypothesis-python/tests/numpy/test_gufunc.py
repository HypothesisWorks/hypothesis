from __future__ import absolute_import

import numpy as np
from hypothesis import given
from hypothesis.strategies import integers, lists, data
import hypothesis.extra.gufunc as gu
# from hypothesis.extra.numpy import scalar_dtypes, from_dtype

# TODO consider if tuple_of_arrays should always return np.array


@given(lists(lists(integers(min_value=0, max_value=5),
                   min_size=0, max_size=3), min_size=0, max_size=5), data())
def test_shapes_tuple_of_arrays(shapes, data):
    S = gu.tuple_of_arrays(shapes, integers, min_value=0, max_value=5)
    L = data.draw(S)

    assert len(shapes) == len(L)
    for spec, drawn in zip(shapes, L):
        assert tuple(spec) == np.shape(drawn)
        # TODO after API change, can make bigger test of elements elsewhere
        assert np.asarray(drawn).dtype == int
        assert np.all(0 <= drawn)
        assert np.all(drawn <= 5)


def test_constraints_gufunc_shape():
    # generate signatures
    #    but also with already parsed
    #    need to generate parsed and do inverse of sig
    # infer shape of each var
    #    make sure never assign dif value if already infered
    #    or correct val if is const
    #    make sure right len
    # test sizes in [min, max] range
    pass


def test_constraints_gufunc():
    # same as gufunc_shape but now need to use .shape to get shapes
    #   => put most of test in subroutine, then test_ func is wrapper
    pass


def test_elements_gufunc():
    # again prob just a wrapper
    pass


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
