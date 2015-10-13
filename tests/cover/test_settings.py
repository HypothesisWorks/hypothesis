# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

import os

import pytest

import hypothesis
from hypothesis.errors import InvalidArgument
from hypothesis.database import ExampleDatabase
from hypothesis.settings import Settings, Verbosity


def test_has_docstrings():
    assert Settings.verbosity.__doc__


original_default = Settings.get_profile('default').max_examples


def setup_function(fn):
    Settings.load_profile('default')
    Settings.register_profile('test_settings', Settings())
    Settings.load_profile('test_settings')


def test_cannot_set_non_settings():
    s = Settings()
    with pytest.raises(AttributeError):
        s.databas_file = u'some_file'


def test_settings_uses_defaults():
    s = Settings()
    assert s.max_examples == Settings.default.max_examples


def test_picks_up_changes_to_defaults():
    Settings.default.max_examples = 18
    assert Settings.default.max_examples == 18
    s = Settings()
    assert s.max_examples == 18


def test_picks_up_changes_to_defaults_when_switching_profiles():
    Settings.register_profile('other_test_settings', Settings())
    Settings.default.max_examples = 18
    assert Settings.default.max_examples == 18
    Settings.load_profile('other_test_settings')
    assert Settings.default.max_examples == original_default
    Settings.load_profile('test_settings')
    assert Settings.default.max_examples == 18


def test_does_not_pick_up_changes_after_instantiation():
    s = Settings()
    orig = s.max_examples
    Settings.default.max_examples = 18
    assert s.max_examples == orig


def test_raises_attribute_error():
    with pytest.raises(AttributeError):
        Settings().kittens


def test_respects_none_database():
    assert Settings(database=None).database is None


def test_settings_can_be_used_as_context_manager_to_change_defaults():
    with Settings(max_examples=12):
        assert Settings.default.max_examples == 12
    assert Settings.default.max_examples == original_default


def test_can_repeatedly_push_the_same_thing():
    s = Settings(max_examples=12)
    t = Settings(max_examples=17)
    assert Settings().max_examples == original_default
    with s:
        assert Settings().max_examples == 12
        with t:
            assert Settings().max_examples == 17
            with s:
                assert Settings().max_examples == 12
                with t:
                    assert Settings().max_examples == 17
                assert Settings().max_examples == 12
            assert Settings().max_examples == 17
        assert Settings().max_examples == 12
    assert Settings().max_examples == original_default


def test_cannot_create_settings_with_invalid_options():
    with pytest.raises(InvalidArgument):
        Settings(a_setting_with_limited_options=u'spoon')


def test_can_set_verbosity():
    Settings(verbosity=Verbosity.quiet)
    Settings(verbosity=Verbosity.normal)
    Settings(verbosity=Verbosity.verbose)


def test_can_not_set_verbosity_to_non_verbosity():
    with pytest.raises(InvalidArgument):
        Settings(verbosity='kittens')


@pytest.mark.parametrize('db', [None, ExampleDatabase()])
def test_inherits_an_empty_database(db):
    assert Settings.default.database is not None
    s = Settings(database=db)
    assert s.database is db
    with s:
        t = Settings()
    assert t.database is db


@pytest.mark.parametrize('db', [None, ExampleDatabase()])
def test_can_assign_database(db):
    x = Settings()
    assert x.database is not None
    x.database = db
    assert x.database is db


def test_can_assign_default_settings():
    try:
        Settings.default = Settings(max_examples=1100)
        assert Settings.default.max_examples == 1100
        with Settings(max_examples=10):
            assert Settings.default.max_examples == 10
        assert Settings.default.max_examples == 1100
    finally:
        # Reset settings.default to default when settings
        # is first loaded
        Settings.default = Settings(max_examples=200)


def test_load_profile():
    Settings.load_profile('default')
    assert Settings.default.max_examples == 200
    assert Settings.default.max_shrinks == 500
    assert Settings.default.min_satisfying_examples == 5

    Settings.register_profile(
        'test',
        Settings(
            max_examples=10,
            max_shrinks=5
        )
    )

    Settings.load_profile('test')

    assert Settings.default.max_examples == 10
    assert Settings.default.max_shrinks == 5
    assert Settings.default.min_satisfying_examples == 5

    Settings.load_profile('default')

    assert Settings.default.max_examples == 200
    assert Settings.default.max_shrinks == 500
    assert Settings.default.min_satisfying_examples == 5


def test_loading_profile_keeps_expected_behaviour():
    Settings.register_profile('ci', Settings(max_examples=10000))
    Settings.load_profile('ci')
    assert Settings().max_examples == 10000
    with Settings(max_examples=5):
        assert Settings().max_examples == 5
    assert Settings().max_examples == 10000


def test_load_non_existent_profile():
    with pytest.raises(hypothesis.errors.InvalidArgument):
        Settings.get_profile('nonsense')


@pytest.mark.skipif(
    os.getenv('HYPOTHESIS_PROFILE') not in (None, 'default'),
    reason='Defaults have been overridden')
def test_runs_tests_with_defaults_from_conftest():
    assert Settings.default.strict
    assert Settings.default.timeout == -1
