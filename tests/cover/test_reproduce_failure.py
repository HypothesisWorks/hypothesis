# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER


from __future__ import division, print_function, absolute_import

import pytest

import hypothesis.strategies as st
from hypothesis import given, reject, reproduce_failure
from hypothesis.core import decode_failure, encode_failure
from hypothesis.errors import DidNotReproduce


@given(st.binary() | st.binary(min_size=100))
def test_encoding_loop(b):
    assert decode_failure(encode_failure(b)) == b


def test_reproduces_the_failure():
    b = b'hello world'
    n = len(b)

    @reproduce_failure(encode_failure(b))
    @given(st.binary(min_size=n, max_size=n))
    def test(x):
        assert x != b

    with pytest.raises(AssertionError):
        test()


def test_errors_if_provided_example_does_not_reproduce_failure():
    b = b'hello world'
    n = len(b)

    @reproduce_failure(encode_failure(b))
    @given(st.binary(min_size=n, max_size=n))
    def test(x):
        assert x == b

    with pytest.raises(DidNotReproduce):
        test()


def test_errors_with_did_not_reproduce_if_the_shape_changes():
    b = b'hello world'
    n = len(b)

    @reproduce_failure(encode_failure(b))
    @given(st.binary(min_size=n + 1, max_size=n + 1))
    def test(x):
        assert x == b

    with pytest.raises(DidNotReproduce):
        test()


def test_errors_with_did_not_reproduce_if_rejected():
    b = b'hello world'
    n = len(b)

    @reproduce_failure(encode_failure(b))
    @given(st.binary(min_size=n, max_size=n))
    def test(x):
        reject()

    with pytest.raises(DidNotReproduce):
        test()
