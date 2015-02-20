# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""Tests specifically around the behaviour of the interaction between falsify
and the database."""

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pytest
from hypothesis import Verifier, given
from hypothesis.database import SQLiteBackend, ExampleDatabase
from hypothesis.settings import Settings
from hypothesis.descriptors import one_of
from hypothesis.internal.compat import text_type, binary_type


def test_puts_arguments_in_the_database_from_falsify():
    database = ExampleDatabase(backend=SQLiteBackend(':memory:'))
    verifier = Verifier(settings=Settings(database=database))
    verifier.falsify(lambda x, y: False, text_type, int)
    assert list(database.storage_for(text_type).fetch()) == ['']
    assert list(database.storage_for(int).fetch()) == [0]


def test_puts_keyword_arguments_in_the_database_from_given():
    database = ExampleDatabase(backend=SQLiteBackend(':memory:'))
    verifier = Verifier(settings=Settings(database=database))

    @given(x=int, verifier=verifier)
    def a_test(x):
        assert False
    with pytest.raises(AssertionError):
        a_test()
    assert list(database.storage_for(int).fetch()) == [0]


def test_puts_elements_of_list_in_database():
    database = ExampleDatabase(backend=SQLiteBackend(':memory:'))
    verifier = Verifier(settings=Settings(database=database))
    verifier.falsify(lambda x: not x, [int])
    assert list(database.storage_for([int]).fetch()) == [[0]]
    assert list(database.storage_for(int).fetch()) == [0]


def test_puts_elements_of_set_in_database():
    database = ExampleDatabase(backend=SQLiteBackend(':memory:'))
    verifier = Verifier(settings=Settings(database=database))
    verifier.falsify(lambda x: not x, {int})
    assert list(database.storage_for([int]).fetch()) == []
    assert list(database.storage_for({int}).fetch()) == [{0}]
    assert list(database.storage_for(int).fetch()) == [0]


def test_puts_branches_of_one_of_in_database():
    database = ExampleDatabase(backend=SQLiteBackend(':memory:'))
    verifier = Verifier(settings=Settings(database=database))
    verifier.falsify(lambda x: isinstance(x, bool), one_of((int, bool)))
    assert list(database.storage_for(int).fetch()) == [0]
    assert list(database.storage_for(bool).fetch()) == []


def test_does_not_put_unicode_substrings_in_database():
    database = ExampleDatabase(backend=SQLiteBackend(':memory:'))
    verifier = Verifier(settings=Settings(database=database))
    verifier.falsify(lambda x: len(x) <= 3, text_type)
    assert len(list(database.storage_for(text_type).fetch())) == 1


def test_does_not_put_binary_substrings_in_database():
    database = ExampleDatabase(backend=SQLiteBackend(':memory:'))
    verifier = Verifier(settings=Settings(database=database))
    verifier.falsify(lambda x: len(x) <= 3, binary_type)
    assert len(list(database.storage_for(binary_type).fetch())) == 1
    assert len(list(database.storage_for(int).fetch())) == 0


def test_can_use_values_in_the_database():
    example = 'Hello world'
    database = ExampleDatabase(backend=SQLiteBackend(':memory:'))
    storage = database.storage_for(text_type)
    storage.save(example)
    verifier = Verifier(settings=Settings(database=database))
    assert verifier.falsify(lambda x: x != example, text_type) == (
        example,
    )
