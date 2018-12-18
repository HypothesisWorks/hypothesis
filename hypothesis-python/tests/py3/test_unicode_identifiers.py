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

from __future__ import absolute_import, division, print_function

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
