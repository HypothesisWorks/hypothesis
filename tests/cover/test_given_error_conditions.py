# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import time

import pytest
from hypothesis import Settings, given, assume
from hypothesis.errors import Timeout, Unsatisfiable
from hypothesis.strategies import booleans, integers


def test_raises_timeout_on_slow_test():
    @given(integers(), settings=Settings(timeout=0.01))
    def test_is_slow(x):
        time.sleep(0.02)

    with pytest.raises(Timeout):
        test_is_slow()


def test_raises_unsatisfiable_if_all_false():
    @given(integers(), settings=Settings(max_examples=50))
    def test_assume_false(x):
        assume(False)

    with pytest.raises(Unsatisfiable):
        test_assume_false()


def test_raises_unsatisfiable_if_all_false_in_finite_set():
    @given(booleans())
    def test_assume_false(x):
        assume(False)

    with pytest.raises(Unsatisfiable):
        test_assume_false()


def testt_does_not_raise_unsatisfiable_if_some_false_in_finite_set():
    @given(booleans())
    def test_assume_x(x):
        assume(x)

    test_assume_x()
