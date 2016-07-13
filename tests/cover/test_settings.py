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

import os
from tempfile import mkdtemp

import pytest

import hypothesis
from hypothesis.errors import InvalidState, InvalidArgument
from hypothesis.database import ExampleDatabase, \
    DirectoryBasedExampleDatabase
from hypothesis._settings import settings, Verbosity, note_deprecation


def test_has_docstrings():
    assert settings.verbosity.__doc__


original_default = settings.get_profile('default').max_examples


def setup_function(fn):
    settings.load_profile('default')
    settings.register_profile('test_settings', settings())
    settings.load_profile('test_settings')


def test_cannot_set_non_settings():
    s = settings()
    with pytest.raises(AttributeError):
        s.databas_file = u'some_file'


def test_settings_uses_defaults():
    s = settings()
    assert s.max_examples == settings.default.max_examples


def test_raises_attribute_error():
    with pytest.raises(AttributeError):
        settings().kittens


def test_respects_none_database():
    assert settings(database=None).database is None


def test_settings_can_be_used_as_context_manager_to_change_defaults():
    with settings(max_examples=12):
        assert settings.default.max_examples == 12
    assert settings.default.max_examples == original_default


def test_can_repeatedly_push_the_same_thing():
    s = settings(max_examples=12)
    t = settings(max_examples=17)
    assert settings().max_examples == original_default
    with s:
        assert settings().max_examples == 12
        with t:
            assert settings().max_examples == 17
            with s:
                assert settings().max_examples == 12
                with t:
                    assert settings().max_examples == 17
                assert settings().max_examples == 12
            assert settings().max_examples == 17
        assert settings().max_examples == 12
    assert settings().max_examples == original_default


def test_cannot_create_settings_with_invalid_options():
    with pytest.raises(InvalidArgument):
        settings(a_setting_with_limited_options=u'spoon')


def test_can_set_verbosity():
    settings(verbosity=Verbosity.quiet)
    settings(verbosity=Verbosity.normal)
    settings(verbosity=Verbosity.verbose)


def test_can_not_set_verbosity_to_non_verbosity():
    with pytest.raises(InvalidArgument):
        settings(verbosity='kittens')


@pytest.mark.parametrize('db', [None, ExampleDatabase()])
def test_inherits_an_empty_database(db):
    assert settings.default.database is not None
    s = settings(database=db)
    assert s.database is db
    with s:
        t = settings()
    assert t.database is db


@pytest.mark.parametrize('db', [None, ExampleDatabase()])
def test_can_assign_database(db):
    x = settings(database=db)
    assert x.database is db


def test_load_profile():
    settings.load_profile('default')
    assert settings.default.max_examples == 200
    assert settings.default.max_shrinks == 500
    assert settings.default.min_satisfying_examples == 5

    settings.register_profile(
        'test',
        settings(
            max_examples=10,
            max_shrinks=5
        )
    )

    settings.load_profile('test')

    assert settings.default.max_examples == 10
    assert settings.default.max_shrinks == 5
    assert settings.default.min_satisfying_examples == 5

    settings.load_profile('default')

    assert settings.default.max_examples == 200
    assert settings.default.max_shrinks == 500
    assert settings.default.min_satisfying_examples == 5


def test_loading_profile_keeps_expected_behaviour():
    settings.register_profile('ci', settings(max_examples=10000))
    settings.load_profile('ci')
    assert settings().max_examples == 10000
    with settings(max_examples=5):
        assert settings().max_examples == 5
    assert settings().max_examples == 10000


def test_load_non_existent_profile():
    with pytest.raises(hypothesis.errors.InvalidArgument):
        settings.get_profile('nonsense')


@pytest.mark.skipif(
    os.getenv('HYPOTHESIS_PROFILE') not in (None, 'default'),
    reason='Defaults have been overridden')
def test_runs_tests_with_defaults_from_conftest():
    assert settings.default.strict
    assert settings.default.timeout == -1


def test_cannot_delete_a_setting():
    x = settings()
    with pytest.raises(AttributeError):
        del x.max_examples
    x.max_examples

    x = settings()
    with pytest.raises(AttributeError):
        del x.foo


def test_deprecate_uses_default():
    with settings(strict=False):
        note_deprecation('Hi')

    with settings(strict=True):
        with pytest.raises(DeprecationWarning):
            note_deprecation('Hi')


def test_cannot_set_settings():
    x = settings()
    with pytest.raises(AttributeError):
        x.max_examples = 'foo'
    with pytest.raises(AttributeError):
        x.database = 'foo'
    assert x.max_examples != 'foo'
    assert x.database != 'foo'


def test_can_have_none_database():
    assert settings(database=None).database is None


def test_can_have_none_database_file():
    assert settings(database_file=None).database is None


def test_can_override_database_file():
    f = mkdtemp()
    x = settings(database_file=f)
    assert isinstance(x.database, DirectoryBasedExampleDatabase)
    assert x.database.path == f


def test_cannot_define_settings_once_locked():
    with pytest.raises(InvalidState):
        settings.define_setting('hi', 'there', 4)


def test_cannot_assign_default():
    with pytest.raises(AttributeError):
        settings.default = settings(max_examples=3)
    assert settings().max_examples != 3


def test_does_not_warn_if_quiet():
    with pytest.warns(None) as rec:
        note_deprecation('This is bad', settings(
            strict=False, verbosity=Verbosity.quiet))
    assert len(rec) == 0
