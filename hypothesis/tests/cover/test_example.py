# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from hypothesis import example, given, strategies as st
from hypothesis.errors import InvalidArgument

from tests.common.utils import fails_with


@example(False).via("Manually specified")
@given(st.booleans())
def test_ok_example_via(x):
    pass


def test_invalid_example_via():
    with pytest.raises(InvalidArgument):
        example(x=False).via(100)  # not a string!
    with pytest.raises(TypeError):
        example(x=False).via("abc", "def")  # too many args


@pytest.mark.parametrize(
    "kw",
    [
        {"condition": None},  # must be a bool
        {"reason": None},  # must be a string
        {"raises": None},  # not a BaseException (or even a type)
        {"raises": int},  # not a BaseException
        {"raises": [Exception]},  # not a tuple
        {"raises": (None,)},  # tuple containing a non-BaseException
        {"raises": ()},  # empty tuple doesn't make sense here
        # raising non-failure exceptions, eg KeyboardInterrupt, is tested below
    ],
    ids=repr,
)
def test_invalid_example_xfail_arguments(kw):
    with pytest.raises(InvalidArgument):
        example(x=False).xfail(**kw)


@example(True).xfail()
@example(True).xfail(reason="ignored for passing tests")
@example(True).xfail(raises=KeyError)
@example(True).xfail(raises=(KeyError, ValueError))
@example(True).xfail(True, reason="...")
@example(False).xfail(condition=False)
@given(st.none())
def test_many_xfail_example_decorators(fails):
    if fails:
        raise KeyError


@fails_with(AssertionError)
@example(x=True).xfail(raises=KeyError)
@given(st.none())
def test_xfail_reraises_non_specified_exception(x):
    assert not x


@fails_with(
    InvalidArgument,
    match=r"@example\(x=True\) raised an expected BaseException\('msg'\), "
    r"but Hypothesis does not treat this as a test failure",
)
@example(True).xfail()
@given(st.none())
def test_must_raise_a_failure_exception(x):
    if x:
        raise BaseException("msg")


@fails_with(
    AssertionError,
    match=r"Expected an exception from @example\(x=None\), but no exception was raised.",
)
@example(None).xfail()
@given(st.none())
def test_error_on_unexpected_pass_base(x):
    pass


@fails_with(
    AssertionError,
    match=r"Expected an AssertionError from @example\(x=None\), but no exception was raised.",
)
@example(None).xfail(raises=AssertionError)
@given(st.none())
def test_error_on_unexpected_pass_single(x):
    pass


@fails_with(
    AssertionError,
    match=r"Expected an AssertionError from @example\(x=None\), but no exception was raised.",
)
@example(None).xfail(raises=(AssertionError,))
@given(st.none())
def test_error_on_unexpected_pass_single_elem_tuple(x):
    pass


@fails_with(
    AssertionError,
    match=r"Expected a KeyError, or ValueError from @example\(x=None\), but no exception was raised.",
)
@example(None).xfail(raises=(KeyError, ValueError))
@given(st.none())
def test_error_on_unexpected_pass_multi(x):
    pass
