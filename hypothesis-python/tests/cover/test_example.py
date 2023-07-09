# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import sys
import warnings
from decimal import Decimal

import pexpect
import pytest

from hypothesis import example, find, given, strategies as st
from hypothesis.errors import (
    HypothesisException,
    InvalidArgument,
    NonInteractiveExampleWarning,
    Unsatisfiable,
)
from hypothesis.internal.compat import WINDOWS

from tests.common.utils import fails_with


def test_example_of_none_is_none():
    assert st.none().example() is None


def test_exception_in_compare_can_still_have_example():
    st.one_of(st.none().map(lambda n: Decimal("snan")), st.just(Decimal(0))).example()


def test_does_not_always_give_the_same_example():
    s = st.integers()
    assert len({s.example() for _ in range(100)}) >= 10


def test_raises_on_no_examples():
    with pytest.raises(Unsatisfiable):
        st.nothing().example()


@fails_with(HypothesisException)
@example(False)
@given(st.booleans())
def test_example_inside_given(b):
    st.integers().example()


@fails_with(HypothesisException)
def test_example_inside_find():
    find(st.integers(0, 100), lambda x: st.integers().example())


@fails_with(HypothesisException)
def test_example_inside_strategy():
    st.booleans().map(lambda x: st.integers().example()).example()


def test_non_interactive_example_emits_warning():
    # We have this warning disabled for most of our tests, because self-testing
    # Hypothesis means `.example()` can be a good idea when it never is for users.
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        with pytest.warns(NonInteractiveExampleWarning):
            st.text().example()


@pytest.mark.skipif(WINDOWS, reason="pexpect.spawn not supported on Windows")
def test_interactive_example_does_not_emit_warning():
    try:
        child = pexpect.spawn(f"{sys.executable} -Werror")
        child.expect(">>> ", timeout=10)
    except pexpect.exceptions.EOF:
        pytest.skip(
            "Unable to run python with -Werror.  This may be because you are "
            "running from an old virtual environment - update your installed "
            "copy of `virtualenv` and then create a fresh environment."
        )
    child.sendline("from hypothesis.strategies import none")
    child.sendline("none().example()")
    child.sendline("quit(code=0)")


def identity(decorator):
    # The "identity function hack" from https://peps.python.org/pep-0614/
    # Method-chaining decorators are otherwise a syntax error in Python <= 3.8
    return decorator


@identity(example(False).via("Manually specified"))
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


@identity(example(True).xfail())
@identity(example(True).xfail(reason="ignored for passing tests"))
@identity(example(True).xfail(raises=KeyError))
@identity(example(True).xfail(raises=(KeyError, ValueError)))
@identity(example(True).xfail(True, reason="..."))
@identity(example(False).xfail(condition=False))
@given(st.none())
def test_many_xfail_example_decorators(fails):
    if fails:
        raise KeyError


@fails_with(AssertionError)
@identity(example(x=True).xfail(raises=KeyError))
@given(st.none())
def test_xfail_reraises_non_specified_exception(x):
    assert not x


@fails_with(
    InvalidArgument,
    match=r"@example\(x=True\) raised an expected BaseException\('msg'\), "
    r"but Hypothesis does not treat this as a test failure",
)
@identity(example(True).xfail())
@given(st.none())
def test_must_raise_a_failure_exception(x):
    if x:
        raise BaseException("msg")


@fails_with(
    AssertionError,
    match=r"Expected an exception from @example\(x=None\), but no exception was raised.",
)
@identity(example(None).xfail())
@given(st.none())
def test_error_on_unexpected_pass_base(x):
    pass


@fails_with(
    AssertionError,
    match=r"Expected an AssertionError from @example\(x=None\), but no exception was raised.",
)
@identity(example(None).xfail(raises=AssertionError))
@given(st.none())
def test_error_on_unexpected_pass_single(x):
    pass


@fails_with(
    AssertionError,
    match=r"Expected an AssertionError from @example\(x=None\), but no exception was raised.",
)
@identity(example(None).xfail(raises=(AssertionError,)))
@given(st.none())
def test_error_on_unexpected_pass_single_elem_tuple(x):
    pass


@fails_with(
    AssertionError,
    match=r"Expected a KeyError, or ValueError from @example\(x=None\), but no exception was raised.",
)
@identity(example(None).xfail(raises=(KeyError, ValueError)))
@given(st.none())
def test_error_on_unexpected_pass_multi(x):
    pass
