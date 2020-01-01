# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

from functools import wraps

import pytest

from hypothesis import given, strategies as st


def always_passes(*args, **kwargs):
    """Stand-in for a fixed version of an inner test.

    For example, pytest-trio would take the inner test, wrap it in an
    async-to-sync converter, and use the new func (not always_passes).
    """


@given(st.integers())
def test_can_replace_inner_test(x):
    assert False, "This should be replaced"


test_can_replace_inner_test.hypothesis.inner_test = always_passes


def decorator(func):
    """An example of a common decorator pattern."""

    @wraps(func)
    def inner(*args, **kwargs):
        return func(*args, **kwargs)

    return inner


@decorator
@given(st.integers())
def test_can_replace_when_decorated(x):
    assert False, "This should be replaced"


test_can_replace_when_decorated.hypothesis.inner_test = always_passes


@pytest.mark.parametrize("x", [1, 2])
@given(y=st.integers())
def test_can_replace_when_parametrized(x, y):
    assert False, "This should be replaced"


test_can_replace_when_parametrized.hypothesis.inner_test = always_passes
