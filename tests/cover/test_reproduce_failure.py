# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

import re
import zlib
import base64

import pytest

import hypothesis.strategies as st
from hypothesis import PrintSettings, given, reject, example, settings, \
    __version__, reproduce_failure
from hypothesis.core import decode_failure, encode_failure
from hypothesis.errors import DidNotReproduce, InvalidArgument
from tests.common.utils import capture_out


@given(st.binary() | st.binary(min_size=100))
def test_encoding_loop(b):
    assert decode_failure(encode_failure(b)) == b


@example(base64.b64encode(b'\2\3\4'))
@example(b'\t')
@given(st.binary())
def test_decoding_may_fail(t):
    try:
        decode_failure(t)
        reject()
    except InvalidArgument:
        pass


def test_reproduces_the_failure():
    b = b'hello world'
    n = len(b)

    @reproduce_failure(__version__, encode_failure(b))
    @given(st.binary(min_size=n, max_size=n))
    def test(x):
        assert x != b

    with pytest.raises(AssertionError):
        test()


def test_errors_if_provided_example_does_not_reproduce_failure():
    b = b'hello world'
    n = len(b)

    @reproduce_failure(__version__, encode_failure(b))
    @given(st.binary(min_size=n, max_size=n))
    def test(x):
        assert x == b

    with pytest.raises(DidNotReproduce):
        test()


def test_errors_with_did_not_reproduce_if_the_shape_changes():
    b = b'hello world'
    n = len(b)

    @reproduce_failure(__version__, encode_failure(b))
    @given(st.binary(min_size=n + 1, max_size=n + 1))
    def test(x):
        assert x == b

    with pytest.raises(DidNotReproduce):
        test()


def test_errors_with_did_not_reproduce_if_rejected():
    b = b'hello world'
    n = len(b)

    @reproduce_failure(__version__, encode_failure(b))
    @given(st.binary(min_size=n, max_size=n))
    def test(x):
        reject()

    with pytest.raises(DidNotReproduce):
        test()


def test_prints_reproduction_if_requested():
    failing_example = [None]

    @settings(print_blob=PrintSettings.ALWAYS, database=None)
    @given(st.integers())
    def test(i):
        if failing_example[0] is None and i > 10 ** 6:
            failing_example[0] = i
        assert i not in failing_example

    with capture_out() as o:
        with pytest.raises(AssertionError):
            test()
    assert '@reproduce_failure' in o.getvalue()

    exp = re.compile(r'reproduce_failure\(([^)]+)\)', re.MULTILINE)
    extract = exp.search(o.getvalue())
    reproduction = eval(extract.group(0))
    test = reproduction(test)

    with pytest.raises(AssertionError):
        test()


def test_does_not_print_reproduction_for_simple_examples_by_default():
    @given(st.integers())
    def test(i):
        assert False

    with capture_out() as o:
        with pytest.raises(AssertionError):
            test()
    assert '@reproduce_failure' not in o.getvalue()


def test_does_print_reproduction_for_simple_data_examples_by_default():
    @given(st.data())
    def test(data):
        data.draw(st.integers())
        assert False

    with capture_out() as o:
        with pytest.raises(AssertionError):
            test()
    assert '@reproduce_failure' in o.getvalue()


def test_does_not_print_reproduction_for_large_data_examples_by_default():
    @settings(max_shrinks=0)
    @given(st.data())
    def test(data):
        b = data.draw(st.binary(min_size=1000, max_size=1000))
        if len(zlib.compress(b)) > 1000:
            raise ValueError()

    with capture_out() as o:
        with pytest.raises(ValueError):
            test()
    assert '@reproduce_failure' not in o.getvalue()


class Foo(object):
    def __repr__(self):
        return 'not a valid python expression'


def test_does_print_reproduction_given_an_invalid_repr():
    @given(st.integers().map(lambda x: Foo()))
    def test(i):
        raise ValueError()

    with capture_out() as o:
        with pytest.raises(ValueError):
            test()

    assert '@reproduce_failure' in o.getvalue()


def test_does_not_print_reproduction_if_told_not_to():
    @settings(print_blob=PrintSettings.NEVER)
    @given(st.integers().map(lambda x: Foo()))
    def test(i):
        raise ValueError()

    with capture_out() as o:
        with pytest.raises(ValueError):
            test()

    assert '@reproduce_failure' not in o.getvalue()


def test_raises_invalid_if_wrong_version():
    b = b'hello world'
    n = len(b)

    @reproduce_failure('1.0.0', encode_failure(b))
    @given(st.binary(min_size=n, max_size=n))
    def test(x):
        pass

    with pytest.raises(InvalidArgument):
        test()
