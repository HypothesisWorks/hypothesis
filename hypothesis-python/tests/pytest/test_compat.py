# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
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

from __future__ import absolute_import, division, print_function

import pytest

from hypothesis.database import InMemoryExampleDatabase
from hypothesis import given, settings
from hypothesis.strategies import booleans


@given(booleans())
@pytest.mark.parametrize("hi", (1, 2, 3))
def test_parametrize_after_given(hi, i):
    pass


DB = InMemoryExampleDatabase()


@settings(database=DB)
@given(booleans())
@pytest.mark.parametrize("hi", (1, 2, 3))
@pytest.mark.xfail()
def test_dummy_for_parametrized_db_keys(hi, i):
    assert False  # Test *must* fail for it to end up the database anyway


def test_DB_keys_for_parametrized_test():
    print(DB.data)
    assert len(DB.data) > 1
