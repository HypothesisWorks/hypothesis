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

import numpy as np
import pytest
from pytest import param

import hypothesis.extra.numpy as nps
import hypothesis.strategies as st
from hypothesis import example, given, note, settings
from hypothesis.errors import InvalidArgument
from tests.common.debug import find_any, minimal


def use_signature_examples(func):
    for sig in [
        "(),()->()",
        "(i)->()",
        "(i),(i)->()",
        "(m,n),(n,p)->(m,p)",
        "(n),(n,p)->(p)",
        "(m,n),(n)->(m)",
        "(m?,n),(n,p?)->(m?,p?)",
        "(3),(3)->(3)",
    ]:
        func = example(sig)(func)
    return func


def hy_sig_2_np_sig(hy_sig):
    return (
        [tuple(d.strip("?") for d in shape) for shape in hy_sig.input_shapes],
        [tuple(d.strip("?") for d in hy_sig.result_shape)],
    )


@use_signature_examples
@example("()->(%s),()" % ",".join(33 * "0"))
@given(st.from_regex(np.lib.function_base._SIGNATURE))
def test_numpy_signature_parses(sig):
    if sig == "(m?,n),(n,p?)->(m?,p?)":  # matmul example
        return

    np_sig = np.lib.function_base._parse_gufunc_signature(sig)
    try:
        hy_sig = nps._hypothesis_parse_gufunc_signature(sig, all_checks=False)
        assert np_sig == hy_sig_2_np_sig(hy_sig)
    except InvalidArgument:
        shape_too_long = any(len(s) > 32 for s in np_sig[0] + np_sig[1])
        multiple_outputs = len(np_sig[1]) > 1
        assert shape_too_long or multiple_outputs

        # Now, if we can fix this up does it validate?
        in_, out = sig.split("->")
        sig = in_ + "->" + out.split(",(")[0]
        np_sig = np.lib.function_base._parse_gufunc_signature(sig)
        if all(len(s) <= 32 for s in np_sig[0] + np_sig[1]):
            hy_sig = nps._hypothesis_parse_gufunc_signature(sig, all_checks=False)
            assert np_sig == hy_sig_2_np_sig(hy_sig)


@use_signature_examples
@given(st.from_regex(nps._SIGNATURE))
def test_hypothesis_signature_parses(sig):
    hy_sig = nps._hypothesis_parse_gufunc_signature(sig, all_checks=False)
    try:
        np_sig = np.lib.function_base._parse_gufunc_signature(sig)
        assert np_sig == hy_sig_2_np_sig(hy_sig)
    except ValueError:
        assert "?" in sig
        # We can always fix this up, and it should then always validate.
        sig = sig.replace("?", "")
        hy_sig = nps._hypothesis_parse_gufunc_signature(sig, all_checks=False)
        np_sig = np.lib.function_base._parse_gufunc_signature(sig)
        assert np_sig == hy_sig_2_np_sig(hy_sig)


def test_frozen_dims_signature():
    nps._hypothesis_parse_gufunc_signature("(2),(3)->(4)")


@st.composite
def gufunc_arrays(draw, shape_strat, **kwargs):
    """An example user strategy built on top of mutually_broadcastable_shapes."""
    input_shapes, result_shape = draw(shape_strat)
    arrays_strat = st.tuples(*(nps.arrays(shape=s, **kwargs) for s in input_shapes))
    return draw(arrays_strat), result_shape


@given(
    gufunc_arrays(
        nps.mutually_broadcastable_shapes(signature=np.matmul.signature),
        dtype="float64",
        elements=st.floats(0, 1000),
    )
)
def test_matmul_gufunc_shapes(everything):
    arrays, result_shape = everything
    out = np.matmul(*arrays)
    assert out.shape == result_shape


@settings(deadline=None, max_examples=10)
@pytest.mark.parametrize(
    "target_sig",
    ("(i),(i)->()", "(m,n),(n,p)->(m,p)", "(n),(n,p)->(p)", "(m,n),(n)->(m)"),
)
@given(data=st.data())
def test_matmul_signature_can_exercise_all_combination_of_optional_dims(
    target_sig, data
):
    target_shapes = data.draw(
        nps.mutually_broadcastable_shapes(signature=target_sig, max_dims=0)
    )
    find_any(
        nps.mutually_broadcastable_shapes(
            signature="(m?,n),(n,p?)->(m?,p?)", max_dims=0
        ),
        lambda shapes: shapes == target_shapes,
        settings(max_examples=10 ** 6),
    )


@settings(deadline=None, max_examples=50)
@given(
    min_dims=st.integers(0, 4),
    min_side=st.integers(2, 3),
    n_fixed=st.booleans(),
    data=st.data(),
)
def test_matmul_sig_shrinks_as_documented(min_dims, min_side, n_fixed, data):
    sig = "(m?,n),(n,p?)->(m?,p?)"
    if n_fixed:
        n_value = data.draw(st.integers(0, 4))
        sig = sig.replace("n", str(n_value))
    else:
        n_value = min_side

    note("signature: {}".format(sig))
    max_dims = data.draw(st.none() | st.integers(min_dims, 4), label="max_dims")
    max_side = data.draw(st.none() | st.integers(min_side, 6), label="max_side")

    smallest_shapes, result = minimal(
        nps.mutually_broadcastable_shapes(
            signature=sig,
            min_side=min_side,
            max_side=max_side,
            min_dims=min_dims,
            max_dims=max_dims,
        )
    )
    note("(smallest_shapes, result): {}".format((smallest_shapes, result)))

    # if min_dims >= 1 then core dims are never excluded
    # otherwise, should shrink towards excluding all optional dims
    expected_input_0 = (
        (n_value,) if min_dims == 0 else (min_side,) * min_dims + (min_side, n_value)
    )
    assert expected_input_0 == smallest_shapes[0]

    expected_input_1 = (
        (n_value,) if min_dims == 0 else (min_side,) * min_dims + (n_value, min_side)
    )
    assert expected_input_1 == smallest_shapes[1]


def gufunc_sig_to_einsum_sig(gufunc_sig):
    """E.g. (i,j),(j,k)->(i,k) becomes ...ij,...jk->...ik"""

    def einlabels(labels):
        assert "x" not in labels, "we reserve x for fixed-dimensions"
        return "..." + "".join(i if not i.isdigit() else "x" for i in labels)

    gufunc_sig = nps._hypothesis_parse_gufunc_signature(gufunc_sig)
    input_sig = ",".join(map(einlabels, gufunc_sig.input_shapes))
    return input_sig + "->" + einlabels(gufunc_sig.result_shape)


@pytest.mark.parametrize(
    ("gufunc_sig"),
    [
        param("()->()", id="unary sum"),
        param("(),()->()", id="binary sum"),
        param("(),(),()->()", id="trinary sum"),
        param("(i)->()", id="sum1d"),
        param("(i,j)->(j)", id="sum rows"),
        param("(i),(i)->()", id="inner1d"),
        param("(i),(i),(i)->()", id="trinary inner1d"),
        param("(m,n),(n,p)->(m,p)", id="matmat"),
        param("(n),(n,p)->(p)", id="vecmat"),
        param("(i,t),(j,t)->(i,j)", id="outer-inner"),
        param("(3),(3)->(3)", id="cross1d"),
        param("(i,j)->(j,i)", id="transpose"),
        param("(i),(j)->(i,j)", id="outer"),
        param("(i,3),(3,k)->(3,i,k)", id="fixed dim outer product"),
        param("(i),(j),(k)->(i,j,k)", id="trinary outer"),
        param("(i,i)->(i)", id="trace"),
        param("(j,i,i,j)->(i,j)", id="bigger trace"),
        param("(k),(j,i,k,i,j),(j,i)->(i,j)", id="trace product"),
    ],
)
@given(data=st.data())
def test_einsum_gufunc_shapes(gufunc_sig, data):
    arrays, result_shape = data.draw(
        gufunc_arrays(
            nps.mutually_broadcastable_shapes(signature=gufunc_sig),
            dtype="float64",
            elements=st.floats(0, 1000),
        ),
        label="arrays, result_shape",
    )
    out = np.einsum(gufunc_sig_to_einsum_sig(gufunc_sig), *arrays)
    assert out.shape == result_shape
