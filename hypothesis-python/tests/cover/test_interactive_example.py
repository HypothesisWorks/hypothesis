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

import pytest

from hypothesis import example, find, given, strategies as st
from hypothesis.errors import (
    HypothesisException,
    InvalidArgument,
    NonInteractiveExampleWarning,
    Unsatisfiable,
)
from hypothesis.internal.compat import WINDOWS

from tests.common.debug import find_any
from tests.common.utils import fails_with, skipif_emscripten

pytest_plugins = "pytester"


# Allow calling .example() without warnings for all tests in this module
@pytest.fixture(scope="function", autouse=True)
def _allow_noninteractive_example():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NonInteractiveExampleWarning)
        yield


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
    find_any(st.booleans().map(lambda x: st.integers().example()))


def test_raises_on_arbitrary_data():
    with pytest.raises(InvalidArgument):
        st.data().example()


def test_non_interactive_example_emits_warning():
    # Revert the effect of the allow_noninteractive_example autouse fixture
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        with pytest.warns(NonInteractiveExampleWarning):
            st.text().example()


EXAMPLE_GENERATING_TEST = """
from hypothesis import strategies as st

def test_interactive_example():
    st.integers().example()
"""


def test_selftests_exception_contains_note(pytester):
    # The note is added by a pytest hook, so we need to run it under pytest in a
    # subenvironment with (effectively) the same toplevel conftest.
    with warnings.catch_warnings():
        warnings.simplefilter("error")

        pytester.makeconftest("from tests.conftest import *")
        result = pytester.runpytest_inprocess(
            pytester.makepyfile(EXAMPLE_GENERATING_TEST), "-p", "no:cacheprovider"
        )
        assert "helper methods in tests.common.debug" in "\n".join(result.outlines)


@skipif_emscripten
@pytest.mark.skipif(WINDOWS, reason="pexpect.spawn not supported on Windows")
def test_interactive_example_does_not_emit_warning():
    import pexpect

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
