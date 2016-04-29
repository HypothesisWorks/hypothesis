# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

from __future__ import division, print_function, absolute_import

import time

import pytest

from hypothesis import given, assume, reject, settings
from hypothesis.errors import Timeout, Unsatisfiable
from hypothesis.strategies import booleans, integers


def test_raises_timeout_on_slow_test():
    @given(integers())
    @settings(timeout=0.01)
    def test_is_slow(x):
        time.sleep(0.02)

    with pytest.raises(Timeout):
        test_is_slow()


def test_raises_unsatisfiable_if_all_false():
    @given(integers())
    @settings(max_examples=50)
    def test_assume_false(x):
        reject()

    with pytest.raises(Unsatisfiable):
        test_assume_false()


def test_raises_unsatisfiable_if_all_false_in_finite_set():
    @given(booleans())
    def test_assume_false(x):
        reject()

    with pytest.raises(Unsatisfiable):
        test_assume_false()


def test_does_not_raise_unsatisfiable_if_some_false_in_finite_set():
    @given(booleans())
    def test_assume_x(x):
        assume(x)

    test_assume_x()
