# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/HypothesisWorks/hypothesis-python)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/HypothesisWorks/hypothesis-python/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

from hypothesis.internal.reflection import proxies


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
