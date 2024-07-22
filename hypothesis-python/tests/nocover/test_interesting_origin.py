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

from hypothesis import given, settings, strategies as st
from hypothesis.internal.compat import ExceptionGroup

from tests.common.utils import flaky


def go_wrong_naive(a, b):
    try:
        assert a + b < 100
        a / b
    except Exception:
        # Hiding the actual problem is terrible, but this pattern can make sense
        # if you're raising a library-specific or semantically meaningful error.
        raise ValueError("Something went wrong")  # noqa


def go_wrong_with_cause(a, b):
    try:
        assert a + b < 100
        a / b
    except Exception as err:
        # Explicit chaining is the *right way* to change exception type.
        raise ValueError("Something went wrong") from err


def go_wrong_coverup(a, b):
    try:
        assert a + b < 100
        a / b
    except Exception:
        # This pattern SHOULD be local enough that it never distinguishes
        # errors in practice... but if it does, we're ready.
        raise ValueError("Something went wrong") from None


@pytest.mark.parametrize(
    "function",
    [go_wrong_naive, go_wrong_with_cause, go_wrong_coverup],
    ids=lambda f: f.__name__,
)
@flaky(max_runs=3, min_passes=1)
def test_can_generate_specified_version(function):
    @given(st.integers(), st.integers())
    @settings(database=None, report_multiple_bugs=True)
    def test_fn(x, y):
        # Indirection to fix https://github.com/HypothesisWorks/hypothesis/issues/2888
        return function(x, y)

    with pytest.raises(ExceptionGroup):
        test_fn()
