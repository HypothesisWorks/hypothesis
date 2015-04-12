# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from unittest import TestCase

import pytest
from hypothesis import given


class TestTryReallyHard(TestCase):

    @given(int)
    def test_something(self, i):
        pass

    def execute_example(self, f):
        f()
        return f()


class Valueless(object):

    def execute_example(self, f):
        try:
            return f()
        except ValueError:
            return None

    @given(int)
    def test_no_boom(self, x):
        raise ValueError()

    @given(int)
    def test_boom(self, x):
        assert False


def test_boom():
    with pytest.raises(AssertionError):
        Valueless().test_boom()


def test_no_boom():
    Valueless().test_no_boom()
