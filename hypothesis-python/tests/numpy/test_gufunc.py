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

import hypothesis.extra.numpy as nps
import hypothesis.strategies as st
from hypothesis import example, given
from hypothesis.errors import InvalidArgument


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
