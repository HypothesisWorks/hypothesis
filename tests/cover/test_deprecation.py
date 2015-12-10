# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import pytest

import hypothesis.strategies as st
from hypothesis import given, Settings, strategy, Verbosity
from hypothesis.settings import HypothesisDeprecationWarning
from hypothesis.specifiers import just
from hypothesis.strategies import booleans


def test_strategy_still_warns_on_strategies(recwarn):
    strategy(booleans(), Settings(strict=False))
    assert recwarn.pop(DeprecationWarning) is not None


def test_given_warns_on_use_of_non_strategies(recwarn):
    @given(bool, settings=Settings(strict=False))
    def test(x):
        pass
    test()
    assert recwarn.pop(DeprecationWarning) is not None


def test_raises_in_strict_mode():
    with pytest.raises(HypothesisDeprecationWarning):
        strategy(just(u'test_raises_in_strict_mode'), Settings(strict=True))


def test_strategy_warns_on_non_strategies(recwarn):
    strategy(
        just(u'test_strategy_warns_on_non_strategies'),
        Settings(strict=False))
    assert recwarn.pop(DeprecationWarning) is not None


def test_given_warns_when_mixing_positional_with_keyword(recwarn):
    given(booleans(), y=booleans(), settings=Settings(strict=False))
    assert recwarn.pop(DeprecationWarning) is not None


def test_given_does_not_warn_when_using_strategies_directly(recwarn):
    @given(booleans(), booleans())
    def foo(x, y):
        pass

    foo()
    with pytest.raises(AssertionError):
        recwarn.pop(DeprecationWarning)


def test_warnings_are_suppressed_in_quiet_mode(recwarn):
    strategy(bool, settings=Settings(strict=False, verbosity=Verbosity.quiet))
    with pytest.raises(AssertionError):
        recwarn.pop(DeprecationWarning)


def test_explicitly_overriding_passed_in_arguments_is_deprecated():
    @given(st.integers())
    def a(x):
        pass

    with pytest.raises(DeprecationWarning):
        a(1)

    with pytest.raises(DeprecationWarning):
        a(x=1)


def test_explicitly_overriding_passed_in_kwargs_is_deprecated():
    @given(t=st.integers())
    def a(**kwargs):
        pass

    with pytest.raises(DeprecationWarning):
        a(t=1)


def test_returning_non_none_is_deprecated():
    @given(st.integers())
    def a(x):
        return 1

    with pytest.raises(DeprecationWarning):
        a()
