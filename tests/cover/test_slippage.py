# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

from hypothesis import given
import hypothesis.strategies as st
import pytest


def test_does_not_slip_into_other_exception_type():
    target = [None]

    @given(st.integers())
    def test(i):
        if abs(i) < 1000:
            return
        if target[0] is None:
            target[0] = i
        exc_class = TypeError if target[0] == i else ValueError
        raise exc_class()

    with pytest.raises(TypeError):
        test()


def test_does_not_slip_into_other_exception_location():
    target = [None]

    @given(st.integers())
    def test(i):
        if abs(i) < 1000:
            return
        if target[0] is None:
            target[0] = i
        if target[0] == i:
            raise ValueError("loc 1")
        else:
            raise ValueError("loc 2")

    with pytest.raises(ValueError) as e:
        test()
    assert e.value.args[0] == "loc 1"
