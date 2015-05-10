# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pytest
from hypothesis import Settings, given, strategy
from hypothesis.specifiers import just
from hypothesis.strategies import booleans
from hypothesis.deprecation import HypothesisDeprecationWarning


def test_strategy_does_not_warn_on_strategies(recwarn):
    strategy(booleans())
    with pytest.raises(AssertionError):
        recwarn.pop(DeprecationWarning)


def test_raises_in_strict_mode():
    with pytest.raises(HypothesisDeprecationWarning):
        strategy(just('test_raises_in_strict_mode'), Settings(strict=True))


def test_strategy_warns_on_non_strategies(recwarn):
    strategy(
        just('test_strategy_warns_on_non_strategies'),
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
