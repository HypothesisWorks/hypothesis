# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

from unittest import TestCase

import pytest
from hypothesis import given, example, reporting
from hypothesis.errors import InvalidArgument
from tests.common.utils import capture_out
from hypothesis.strategies import text, integers
from hypothesis.internal.compat import integer_types


class TestInstanceMethods(TestCase):

    @given(integers())
    @example(1)
    def test_hi_1(self, x):
        assert isinstance(x, integer_types)

    @given(integers())
    @example(x=1)
    def test_hi_2(self, x):
        assert isinstance(x, integer_types)

    @given(x=integers())
    @example(x=1)
    def test_hi_3(self, x):
        assert isinstance(x, integer_types)


def test_kwarg_example_on_testcase():
    class Stuff(TestCase):

        @given(integers())
        @example(x=1)
        def test_hi(self, x):
            assert isinstance(x, integer_types)

    Stuff(u'test_hi').test_hi()


def test_errors_when_run_with_not_enough_args():
    @given(integers(), int)
    @example(1)
    def foo(x, y):
        pass

    with pytest.raises(TypeError):
        foo()


def test_errors_when_run_with_not_enough_kwargs():
    @given(integers(), int)
    @example(x=1)
    def foo(x, y):
        pass

    with pytest.raises(TypeError):
        foo()


def test_can_use_examples_after_given():
    long_str = u"This is a very long string that you've no chance of hitting"

    @example(long_str)
    @given(text())
    def test_not_long_str(x):
        assert x != long_str

    with pytest.raises(AssertionError):
        test_not_long_str()


def test_can_use_examples_before_given():
    long_str = u"This is a very long string that you've no chance of hitting"

    @given(text())
    @example(long_str)
    def test_not_long_str(x):
        assert x != long_str

    with pytest.raises(AssertionError):
        test_not_long_str()


def test_can_use_examples_around_given():
    long_str = u"This is a very long string that you've no chance of hitting"
    short_str = u'Still no chance'

    seen = []

    @example(short_str)
    @given(text())
    @example(long_str)
    def test_not_long_str(x):
        seen.append(x)

    test_not_long_str()
    assert set(seen[:2]) == set((long_str, short_str))


@pytest.mark.parametrize((u'x', u'y'), [(1, False), (2, True)])
@example(z=10)
@given(z=integers())
def test_is_a_thing(x, y, z):
    pass


def test_no_args_and_kwargs():
    with pytest.raises(InvalidArgument):
        example(1, y=2)


def test_no_empty_examples():
    with pytest.raises(InvalidArgument):
        example()


def test_does_not_print_on_explicit_examples_if_no_failure():
    @example(1)
    @given(integers())
    def test_positive(x):
        assert x > 0

    with reporting.with_reporter(reporting.default):
        with pytest.raises(AssertionError):
            with capture_out() as out:
                test_positive()
    out = out.getvalue()
    assert u'Falsifying example: test_positive(1)' not in out


def test_prints_output_for_explicit_examples():
    @example(-1)
    @given(integers())
    def test_positive(x):
        assert x > 0

    with reporting.with_reporter(reporting.default):
        with pytest.raises(AssertionError):
            with capture_out() as out:
                test_positive()
    out = out.getvalue()
    assert u'Falsifying example: test_positive(x=-1)' in out


def test_captures_original_repr_of_example():
    @example(x=[])
    @given(integers())
    def test_mutation(x):
        x.append(1)
        assert not x

    with reporting.with_reporter(reporting.default):
        with pytest.raises(AssertionError):
            with capture_out() as out:
                test_mutation()
    out = out.getvalue()
    assert u'Falsifying example: test_mutation(x=[])' in out
