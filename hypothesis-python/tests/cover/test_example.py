# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
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

import sys
import warnings
from decimal import Decimal

import pexpect
import pytest

from hypothesis import example, find, given, strategies as st
from hypothesis.errors import (
    HypothesisException,
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
