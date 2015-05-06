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
from hypothesis import Settings, given, assume
from hypothesis.errors import Unsatisfiable
from hypothesis.database import ExampleDatabase


def test_finite_space_errors_if_all_unsatisfiable():
    @given(booleans())
    def test_no(x):
        assume(False)

    with pytest.raises(Unsatisfiable):
        test_no()


def test_finite_space_does_not_error_if_some_unsatisfiable():
    @given(booleans())
    def test_check(x):
        assume(x)

    test_check()


def test_finite_test_does_not_fail_if_example_comes_from_db():
    is_bad = [True]

    @given((), settings=Settings(database=ExampleDatabase()))
    def is_not_bad(x):
        assert not is_bad[0]

    with pytest.raises(AssertionError):
        is_not_bad()

    is_bad[0] = False

    is_not_bad()
