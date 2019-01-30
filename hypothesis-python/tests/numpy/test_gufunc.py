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

from __future__ import absolute_import, division, print_function

import string
from collections import defaultdict
from functools import reduce

import numpy as np
import numpy.lib.function_base as npfb

import hypothesis.extra.gufunc as gu
from hypothesis import given
from hypothesis.errors import InvalidArgument
from hypothesis.extra.numpy import from_dtype, scalar_dtypes
from hypothesis.internal.compat import hunichr, integer_types
from hypothesis.strategies import (
    booleans,
    composite,
    data,
    dictionaries,
    from_regex,
    integers,
    just,
    lists,
    one_of,
    sampled_from,
    sets,
    tuples,
)

# Use to sample from simple names, we also can sample from npfb._SIGNATURE
# regex to get all possible signatures. This regex also doesn't start with
# digits because if it is parsed as number we could end up with very large
# dimensions that blow out memory.
VALID_DIM_NAMES = r"\A[a-zA-Z_][a-zA-Z0-9_]*\Z"

_st_shape = lists(integers(min_value=0, max_value=5), min_size=0, max_size=3).map(tuple)


def no_weird_digits(ss):
    ok = all((not cc.isdigit()) or (cc in string.digits) for cc in ss)
    return ok


def pad_left(L, size, padding):
    L = (padding,) * max(0, size - len(L)) + L
    return L


def validate_elements(L, dtype, unique=False, choices=None):
    for drawn in L:
        assert drawn.dtype == np.dtype(dtype)

        if unique:
            assert len(set(drawn.ravel())) == drawn.size

        if choices is not None:
            assert drawn.dtype == choices.dtype
            vals = set(drawn.ravel())
            assert vals.issubset(choices)


def validate_shapes(L, parsed_sig, min_side, max_side):
    assert type(L) == list
    assert len(parsed_sig) == len(L)
    size_lookup = {}
    for spec, drawn in zip(parsed_sig, L):
        assert type(drawn) == tuple
        assert len(spec) == len(drawn)
        for ss, dd in zip(spec, drawn):
            assert isinstance(dd, integer_types)
            if ss.isdigit():
                assert int(ss) == dd
            else:
                mm = min_side.get(ss, 0) if isinstance(min_side, dict) else min_side
                assert mm <= dd
                mm = (
                    max_side.get(ss, gu.DEFAULT_MAX_SIDE)
                    if isinstance(max_side, dict)
                    else max_side
                )
                assert dd <= mm
                var_size = size_lookup.setdefault(ss, dd)
                assert var_size == dd


def validate_bcast_shapes(
    shapes, parsed_sig, excluded, min_side, max_side, max_dims_extra
):
    # Ok to be above GLOBAL_DIMS_MAX if core dims are too
    assert all(
        len(ss) <= gu.GLOBAL_DIMS_MAX or len(ss) == len(pp)
        for ss, pp in zip(shapes, parsed_sig)
    )

    assert type(shapes) is list
    assert all(type(ss) is tuple for ss in shapes)
    assert all(all(type(v) is int for v in ss) for ss in shapes)

    assert all(
        (ii not in excluded) or len(ss) == len(pp)
        for ii, (ss, pp) in enumerate(zip(shapes, parsed_sig))
    )

    # chop off extra dims then same as gufunc_shape
    core_dims = [tt[len(tt) - len(pp) :] for tt, pp in zip(shapes, parsed_sig)]
    validate_shapes(core_dims, parsed_sig, min_side, max_side)

    # check max_dims_extra
    b_dims = [tt[: len(tt) - len(pp)] for tt, pp in zip(shapes, parsed_sig)]
    assert all(len(tt) <= max_dims_extra for tt in b_dims)

    # Convert dims to matrix form
    b_dims2 = np.array([pad_left(bb, max_dims_extra, 1) for bb in b_dims], dtype=int)
    # The extra broadcast dims be set to one regardless of min, max sides
    mm = min_side.get(gu.BCAST_DIM, 0) if isinstance(min_side, dict) else min_side
    assert np.all((b_dims2 == 1) | (mm <= b_dims2))
    mm = (
        max_side.get(gu.BCAST_DIM, gu.DEFAULT_MAX_SIDE)
        if isinstance(max_side, dict)
        else max_side
    )
    assert np.all((b_dims2 == 1) | (b_dims2 <= mm))
    # make sure 1 or same
    for ii in range(max_dims_extra):
        vals = set(b_dims2[:, ii])
        # Must all be 1 or a const size
        assert len(vals) <= 2
        assert len(vals) < 2 or (1 in vals)


def assertInvalidArgument(f, *args, **kwargs):
    try:
        f(*args, **kwargs)
    except InvalidArgument:
        return
    assert False, "expected InvalidArgument exception"


def unparse(parsed_sig):
    assert len(parsed_sig) > 0, "gufunc sig does not support no argument funcs"

    i_sig = [",".join(vv) for vv in parsed_sig[0]]
    i_sig = "(" + "),(".join(i_sig) + ")"

    o_sig = [",".join(vv) for vv in parsed_sig[1]]
    o_sig = "(" + "),(".join(o_sig) + ")"

    sig = "->".join((i_sig, o_sig))
    return sig


def real_scalar_dtypes():
    def to_native(dtype):
        tt = dtype.type
        # Only keep if invertible
        tt = tt if np.dtype(tt) == dtype else dtype
        return tt

    def cast_it(args):
        return args[0](args[1])

    dtypes = scalar_dtypes()
    return one_of(dtypes, dtypes.map(str), dtypes.map(to_native))


def real_from_dtype(dtype, N=10):
    dtype = np.dtype(dtype)

    def clean_up(x):
        x = np.nan_to_num(x).astype(dtype)
        assert x.dtype == dtype  # hard to always get this it seems
        return x

    S = lists(from_dtype(dtype), min_size=N, max_size=N).map(clean_up)
    return S


def parsed_sigs(big=False):
    """Strategy to generate a parsed gufunc signature.

    Note that in general functions can take no-args, but the function signature
    formalism is for >= 1 args. So, there is always at least 1 arg here.
    """
    max_dims = 3
    max_args = 5
    # Use | to sample from digits since we would like (small) pure numbers too
    shapes = lists(
        from_regex(VALID_DIM_NAMES) | sampled_from(string.digits),
        min_size=0,
        max_size=max_dims,
    ).map(tuple)
    S = lists(shapes, min_size=1, max_size=max_args)
    S = tuples(S, S)

    if big:
        # Or throw in anything compatible with regex sig
        all_sigs = from_regex(npfb._SIGNATURE).filter(no_weird_digits)
        S |= all_sigs.map(gu.parse_gufunc_signature)

    return S


@composite
def parsed_sigs_and_sizes(draw, big=False):
    min_min_side = 0
    max_max_side = 100 if big else 5

    parsed_sig = draw(parsed_sigs(big))
    # list of all labels used in sig, includes ints which is ok to include in
    # dict as distractors.
    labels = list(set([k for arg in parsed_sig[0] for k in arg]))
    # Also sometimes put the broadcast flag in as label
    labels.append(gu.BCAST_DIM)

    # Using a split to decide which numbers we use for min sides and which
    # numbers we use for max side, to avoid min > max. This strategy does not
    # cover whole search space, but should should be good enough.
    split = draw(integers(min_min_side, gu.DEFAULT_MAX_SIDE))

    if draw(booleans()):
        min_side = draw(
            dictionaries(sampled_from(labels), integers(min_min_side, split))
        )
    else:
        min_side = draw(integers(min_min_side, split))

    if draw(booleans()):
        max_side = draw(
            dictionaries(sampled_from(labels), integers(split, max_max_side))
        )
    else:
        max_side = draw(integers(split, max_max_side))

    return parsed_sig, min_side, max_side


def test_check_functions():
    assertInvalidArgument(gu._check_valid_size_interval, "1", 5, "")
    assertInvalidArgument(gu._check_valid_size_interval, 1, "5", "")
    assertInvalidArgument(gu._check_valid_size_interval, 5, 1, "")
    assertInvalidArgument(gu._check_valid_size_interval, 0, 5, "", floor=1)

    assertInvalidArgument(gu._int_or_dict, {}, "5")
    assertInvalidArgument(gu._int_or_dict, "1", 5)

    assertInvalidArgument(gu.gufunc_arg_shapes, "()->()", max_dims_extra="5")
    assertInvalidArgument(gu.gufunc_arg_shapes, "()->()", max_dims_extra=-1)
    assertInvalidArgument(gu.gufunc_arg_shapes, "()->()", max_dims_extra=50)


@given(parsed_sigs(big=True))
def test_unparse_parse(sig):
    i_parsed_sig, o_parsed_sig = sig

    # We don't care about the output for this function
    signature = unparse((i_parsed_sig, o_parsed_sig))
    # This is a 'private' function of np, so need to test it still works as we
    # think it does.
    inp, out = gu.parse_gufunc_signature(signature)

    assert i_parsed_sig == inp
    assert o_parsed_sig == out


def test_check_set_like():
    """Need for 100% coverage"""
    assertInvalidArgument(gu._check_set_like, 0)
    assertInvalidArgument(gu._check_set_like, "0")
    assertInvalidArgument(gu._check_set_like, "foobar")


@given(dictionaries(from_regex(VALID_DIM_NAMES), integers()), integers(), integers())
def test_ddict_int_or_dict(D, default_val, default_val2):
    DD = defaultdict(lambda: default_val, D)

    DD2 = gu._int_or_dict(DD, default_val2)

    # just pass thru
    assert DD is DD2
    # default_val2 is ignored
    assert DD2.default_factory() == default_val


@given(dictionaries(from_regex(VALID_DIM_NAMES), integers()), integers())
def test_dict_int_or_dict(D, default_val):
    DD = gu._int_or_dict(D, default_val)

    assert DD == D
    assert DD["---"] == default_val


@given(integers(), integers())
def test_int_int_or_dict(default_val, default_val2):
    DD = gu._int_or_dict(default_val, default_val2)

    assert len(DD) == 0
    assert DD["---"] == default_val


@given(real_scalar_dtypes(), _st_shape, data())
def test_arrays(dtype, shape, data):
    # unique argument to arrays gets tested in the tuple of arrays tests
    choices = data.draw(real_from_dtype(dtype))

    elements = sampled_from(choices)
    S = gu._arrays(dtype, shape, elements)
    X = data.draw(S)

    assert np.shape(X) == shape
    validate_elements([X], dtype=dtype, choices=choices)

    assert type(X) == np.ndarray


@given(real_scalar_dtypes(), _st_shape, data())
def test_just_arrays(dtype, shape, data):
    # unique argument to arrays gets tested in the tuple of arrays tests
    choices = data.draw(real_from_dtype(dtype))

    # test again, but this time pass in strategy to make sure it can handle it
    elements = sampled_from(choices)
    S = gu._arrays(just(dtype), just(shape), elements)
    X = data.draw(S)

    assert np.shape(X) == shape
    validate_elements([X], dtype=dtype, choices=choices)

    assert type(X) == np.ndarray


# hypothesis.extra.numpy.array_shapes does not support 0 min_size so we roll
# our own in this case.
@given(
    lists(_st_shape, min_size=0, max_size=5), real_scalar_dtypes(), booleans(), data()
)
def test_shapes_tuple_of_arrays(shapes, dtype, unique, data):
    elements = from_dtype(np.dtype(dtype))

    S = gu._tuple_of_arrays(shapes, dtype, elements=elements, unique=unique)
    X = data.draw(S)

    validate_elements(X, dtype=dtype, unique=unique)

    assert len(shapes) == len(X)
    for spec, drawn in zip(shapes, X):
        assert tuple(spec) == np.shape(drawn)


# hypothesis.extra.numpy.array_shapes does not support 0 min_size so we roll
# our own in this case.
@given(
    lists(_st_shape, min_size=0, max_size=5), real_scalar_dtypes(), booleans(), data()
)
def test_just_shapes_tuple_of_arrays(shapes, dtype, unique, data):
    elements = from_dtype(np.dtype(dtype))

    # test again, but this time pass in strategy to make sure it can handle it
    S = gu._tuple_of_arrays(
        just(shapes), just(dtype), elements=elements, unique=just(unique)
    )
    X = data.draw(S)

    validate_elements(X, dtype=dtype, unique=unique)

    assert len(shapes) == len(X)
    for spec, drawn in zip(shapes, X):
        assert tuple(spec) == np.shape(drawn)


@given(lists(_st_shape, min_size=0, max_size=5), real_scalar_dtypes(), data())
def test_elements_tuple_of_arrays(shapes, dtype, data):
    choices = data.draw(real_from_dtype(dtype))

    elements = sampled_from(choices)
    S = gu._tuple_of_arrays(shapes, dtype, elements=elements)
    X = data.draw(S)

    validate_elements(X, choices=choices, dtype=dtype)


@given(
    gu.gufunc_args(
        "(1),(1),(1),()->()",
        dtype=["object", "object", "object", "bool"],
        elements=[_st_shape, scalar_dtypes(), just(None), booleans()],
        min_side=1,
        max_dims_extra=1,
    ),
    data(),
)
def test_bcast_tuple_of_arrays(args, data):
    """Now testing broadcasting of tuple_of_arrays, kind of crazy since it uses
    gufuncs to test itself. Some awkwardness here since there are a lot of
    corner cases when dealing with object types in the numpy extension.

    For completeness, should probably right a function like this for the other
    functions, but there always just pass dtype, elements, unique to
    `_tuple_of_arrays` anyway, so this should be pretty good.
    """
    shapes, dtype, elements, unique = args

    shapes = shapes.ravel()
    # Need to squeeze out due to weird behaviour of object
    dtype = np.squeeze(dtype, -1)
    elements = np.squeeze(elements, -1)

    elements_shape = max(dtype.shape, elements.shape)
    dtype_ = np.broadcast_to(dtype, elements_shape)
    if elements_shape == ():
        elements = from_dtype(dtype_.item())
    else:
        elements = [from_dtype(dd) for dd in dtype_]

    shapes_shape = max(shapes.shape, dtype.shape, elements_shape, unique.shape)
    shapes = np.broadcast_to(shapes, shapes_shape)

    S = gu._tuple_of_arrays(shapes, dtype, elements=elements, unique=unique)
    X = data.draw(S)

    assert len(shapes) == len(X)
    for spec, drawn in zip(shapes, X):
        assert tuple(spec) == np.shape(drawn)

    for ii, xx in enumerate(X):
        dd = dtype[ii] if dtype.size > 1 else dtype.item()
        uu = unique[ii] if unique.size > 1 else unique.item()
        validate_elements([xx], dtype=dd, unique=uu)


@given(parsed_sigs(big=True))
def test_const_signature_map(parsed_sig):
    parsed_sig, _ = parsed_sig

    # Map all dims to zero
    all_dims = reduce(set.union, [set(arg) for arg in parsed_sig])
    map_dict = {k: 0 for k in all_dims}

    p_ = gu._signature_map(map_dict, parsed_sig)

    assert all(all(v == 0 for v in arg) for arg in p_)


@given(parsed_sigs(big=True))
def test_inverse_signature_map(parsed_sig):
    parsed_sig, _ = parsed_sig

    # Build an arbitrary map
    all_dims = sorted(reduce(set.union, [set(arg) for arg in parsed_sig]))
    map_dict = dict(zip(all_dims, all_dims[::-1]))

    inv_map = {v: k for k, v in map_dict.items()}

    p_ = gu._signature_map(map_dict, parsed_sig)
    p_ = gu._signature_map(inv_map, p_)

    assert p_ == parsed_sig


# Allow bigger sizes since we only generate the shapes and never alloc arrays
# Try +3 to see what happens if we put something too big in
@given(parsed_sigs_and_sizes(big=True), data())
def test_shapes_gufunc_arg_shapes(parsed_sig_and_size, data):
    parsed_sig, min_side, max_side = parsed_sig_and_size

    # This private function assumes already preprocessed sizes to default dict
    min_side = gu._int_or_dict(min_side, 0)
    max_side = gu._int_or_dict(max_side, gu.DEFAULT_MAX_SIDE)

    S = gu._gufunc_arg_shapes(parsed_sig[0], min_side=min_side, max_side=max_side)

    shapes = data.draw(S)
    validate_shapes(shapes, parsed_sig[0], min_side, max_side)


def test_validation_gufunc_arg_shapes():
    sig_template_1 = u"(3),(%s)->()"
    sig_template_2 = u"(x,4),(foo%s)->(5)"
    weird_chars = (1632, 1633, 1634, 65303, 65304, 65305)  # There are more

    for cc in weird_chars:
        assertInvalidArgument(gu.gufunc_arg_shapes, sig_template_1 % hunichr(cc))
        assertInvalidArgument(gu.gufunc_arg_shapes, sig_template_2 % hunichr(cc))


@given(parsed_sigs_and_sizes(big=False), real_scalar_dtypes(), booleans(), data())
def test_shapes_gufunc_args(parsed_sig_and_size, dtype, unique, data):
    parsed_sig, min_side, max_side = parsed_sig_and_size

    signature = unparse(parsed_sig)

    # We could also test using elements strategy that then requires casting,
    # but that would be kind of complicated to come up with compatible combos
    elements = from_dtype(np.dtype(dtype))

    # Assumes zero broadcast dims by default
    S = gu.gufunc_args(
        signature,
        min_side=min_side,
        max_side=max_side,
        dtype=dtype,
        elements=elements,
        unique=unique,
    )

    X = data.draw(S)
    shapes = [np.shape(xx) for xx in X]

    validate_shapes(shapes, parsed_sig[0], min_side, max_side)
    validate_elements(X, dtype=dtype, unique=unique)


@given(
    parsed_sigs(big=False), integers(0, 5), integers(0, 5), real_scalar_dtypes(), data()
)
def test_elements_gufunc_args(parsed_sig, min_side, max_side, dtype, data):
    choices = data.draw(real_from_dtype(dtype))
    elements = sampled_from(choices)

    signature = unparse(parsed_sig)

    min_side, max_side = sorted([min_side, max_side])

    S = gu.gufunc_args(
        signature, min_side=min_side, max_side=max_side, dtype=dtype, elements=elements
    )

    X = data.draw(S)

    validate_elements(X, choices=choices, dtype=dtype)


@given(
    gu.gufunc_args(
        "(n),(m),(n,m),(n)->()",
        dtype=["object", int, bool, int],
        elements=[_st_shape, integers(0, 100), booleans(), integers(0, 100)],
        min_side={"n": 1},
    )
)  # always at least one arg
def test_append_bcast_dims(args):
    core_dims, b_dims, set_to_1, n_extra_per_arg = args

    max_extra = len(b_dims)
    # Put all in range [0, max_extra]
    n_extra_per_arg = tuple(n_extra_per_arg % (max_extra + 1))

    shapes = gu._append_bcast_dims(core_dims, b_dims, set_to_1, n_extra_per_arg)

    for ii, ss in enumerate(shapes):
        bb = np.asarray(ss[: len(ss) - len(core_dims[ii])])
        cc = ss[len(ss) - len(core_dims[ii]) :]

        st1 = set_to_1[ii]
        st1 = st1[len(st1) - len(bb) :]

        assert len(bb) == n_extra_per_arg[ii]
        assert cc == core_dims[ii]
        assert np.all(bb[st1] == 1)
        assert np.all(bb[~st1] == b_dims[len(b_dims) - len(bb) :][~st1])


@given(parsed_sigs_and_sizes(big=True), integers(0, gu.GLOBAL_DIMS_MAX), data())
def test_broadcast_shapes_gufunc_arg_shapes(parsed_sig_and_size, max_dims_extra, data):
    parsed_sig, min_side, max_side = parsed_sig_and_size

    signature = unparse(parsed_sig)
    parsed_sig, _ = parsed_sig

    excluded = data.draw(sets(integers(0, len(parsed_sig) - 1)).map(tuple))

    S = gu.gufunc_arg_shapes(
        signature,
        excluded=excluded,
        min_side=min_side,
        max_side=max_side,
        max_dims_extra=max_dims_extra,
    )

    shapes = data.draw(S)

    validate_bcast_shapes(
        shapes, parsed_sig, excluded, min_side, max_side, max_dims_extra
    )


@given(
    parsed_sigs_and_sizes(big=False),
    integers(0, 3),
    real_scalar_dtypes(),
    booleans(),
    data(),
)
def test_broadcast_shapes_gufunc_args(
    parsed_sig_and_size, max_dims_extra, dtype, unique, data
):
    parsed_sig, min_side, max_side = parsed_sig_and_size

    signature = unparse(parsed_sig)
    parsed_sig, _ = parsed_sig

    excluded = data.draw(sets(integers(0, len(parsed_sig) - 1)).map(tuple))

    elements = from_dtype(np.dtype(dtype))

    S = gu.gufunc_args(
        signature,
        excluded=excluded,
        min_side=min_side,
        max_side=max_side,
        max_dims_extra=max_dims_extra,
        dtype=dtype,
        elements=elements,
        unique=unique,
    )

    X = data.draw(S)
    shapes = [np.shape(xx) for xx in X]

    validate_bcast_shapes(
        shapes, parsed_sig, excluded, min_side, max_side, max_dims_extra
    )
    validate_elements(X, dtype=dtype, unique=unique)


@given(
    parsed_sigs(big=False),
    integers(0, 5),
    integers(0, 5),
    integers(0, 3),
    real_scalar_dtypes(),
    data(),
)
def test_broadcast_elements_gufunc_args(
    parsed_sig, min_side, max_side, max_dims_extra, dtype, data
):
    signature = unparse(parsed_sig)
    parsed_sig, _ = parsed_sig

    excluded = data.draw(sets(integers(0, len(parsed_sig) - 1)).map(tuple))

    min_side, max_side = sorted([min_side, max_side])

    choices = data.draw(real_from_dtype(dtype))
    elements = sampled_from(choices)

    S = gu.gufunc_args(
        signature,
        excluded=excluded,
        min_side=min_side,
        max_side=max_side,
        max_dims_extra=max_dims_extra,
        dtype=dtype,
        elements=elements,
    )

    X = data.draw(S)

    validate_elements(X, choices=choices, dtype=dtype)
