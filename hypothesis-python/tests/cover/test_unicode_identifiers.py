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

from hypothesis import given, strategies as st
from hypothesis.internal.reflection import get_pretty_function_description, proxies


def test_can_copy_argspec_of_unicode_args():
    def foo(μ):
        return μ

    @proxies(foo)
    def bar(μ):
        return foo(μ)

    assert bar(1) == 1


def test_can_copy_argspec_of_unicode_name():
    def ā():
        return 1

    @proxies(ā)
    def bar():
        return 2

    assert bar() == 2


is_approx_π = lambda x: x == 3.1415  # noqa: E731


def test_can_handle_unicode_identifier_in_same_line_as_lambda_def():
    assert get_pretty_function_description(is_approx_π) == "lambda x: x == 3.1415"


def test_regression_issue_1700():
    π = 3.1415

    @given(st.floats(min_value=-π, max_value=π).filter(lambda x: abs(x) > 1e-5))
    def test_nonzero(x):
        assert x != 0

    test_nonzero()
