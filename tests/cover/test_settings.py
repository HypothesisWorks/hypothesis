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

import pytest

import hypothesis
from hypothesis.errors import InvalidArgument
from hypothesis.database import ExampleDatabase
from hypothesis.settings import Settings, Verbosity

TEST_DESCRIPTION = u'This is a setting just for these tests'

Settings.define_setting(
    u'a_setting_just_for_these_tests',
    default=3,
    description=TEST_DESCRIPTION,
)


Settings.define_setting(
    u'a_setting_with_limited_options',
    default=3, description=u'Something something spoon',
    options=(1, 2, 3, 4),
)


def test_has_docstrings():
    assert TEST_DESCRIPTION in Settings.a_setting_just_for_these_tests.__doc__


def setup_function(fn):
    try:
        delattr(Settings.default, u'a_setting_just_for_these_tests')
    except AttributeError:
        pass


def test_cannot_set_non_settings():
    s = Settings()
    with pytest.raises(AttributeError):
        s.databas_file = u'some_file'


def test_settings_uses_defaults():
    s = Settings()
    assert s.a_setting_just_for_these_tests == 3


def test_picks_up_changes_to_defaults():
    Settings.default.a_setting_just_for_these_tests = 18
    assert Settings.default.a_setting_just_for_these_tests == 18
    s = Settings()
    assert s.a_setting_just_for_these_tests == 18


def test_does_not_pick_up_changes_after_instantiation():
    s = Settings()
    Settings.default.a_setting_just_for_these_tests = 18
    assert s.a_setting_just_for_these_tests == 3


def test_raises_attribute_error():
    with pytest.raises(AttributeError):
        Settings().kittens


def test_respects_none_database():
    assert Settings(database=None).database is None


def test_settings_can_be_used_as_context_manager_to_change_defaults():
    with Settings(a_setting_just_for_these_tests=12):
        assert Settings.default.a_setting_just_for_these_tests == 12
    assert Settings.default.a_setting_just_for_these_tests == 3


def test_can_repeatedly_push_the_same_thing():
    s = Settings(a_setting_just_for_these_tests=12)
    t = Settings(a_setting_just_for_these_tests=17)
    assert Settings().a_setting_just_for_these_tests == 3
    with s:
        assert Settings().a_setting_just_for_these_tests == 12
        with t:
            assert Settings().a_setting_just_for_these_tests == 17
            with s:
                assert Settings().a_setting_just_for_these_tests == 12
                with t:
                    assert Settings().a_setting_just_for_these_tests == 17
                assert Settings().a_setting_just_for_these_tests == 12
            assert Settings().a_setting_just_for_these_tests == 17
        assert Settings().a_setting_just_for_these_tests == 12
    assert Settings().a_setting_just_for_these_tests == 3


def test_cannot_create_settings_with_invalid_options():
    with pytest.raises(InvalidArgument):
        Settings(a_setting_with_limited_options=u'spoon')


def test_can_create_settings_with_valid_options():
    Settings(a_setting_with_limited_options=1)


def test_cannot_define_a_setting_with_default_not_valid():
    with pytest.raises(InvalidArgument):
        Settings.define_setting(
            u'kittens',
            default=8, description=u'Kittens are pretty great',
            options=(1, 2, 3, 4),
        )


def test_can_set_verbosity():
    Settings(verbosity=Verbosity.quiet)
    Settings(verbosity=Verbosity.normal)
    Settings(verbosity=Verbosity.verbose)


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


def test_loading_profile_resets_defaults():
    assert Settings.default.min_satisfying_examples == 5
    Settings.default.min_satisfying_examples = 100
    assert Settings.default.min_satisfying_examples == 100
    Settings.load_profile('default')
    assert Settings.default.min_satisfying_examples == 5


def test_loading_profile_keeps_expected_behaviour():
    Settings.register_profile('ci', Settings(max_examples=10000))
    Settings.load_profile('ci')
    assert Settings().max_examples == 10000
    with Settings(max_examples=5):
        assert Settings().max_examples == 5
    assert Settings().max_examples == 10000


def test_modifying_registered_profile_does_not_change_profile():
    ci_profile = Settings(max_examples=10000)
    Settings.register_profile('ci', ci_profile)
    ci_profile.max_examples = 1
    Settings.load_profile('ci')
    assert Settings().max_examples == 10000


def test_load_non_existent_profile():
    with pytest.raises(hypothesis.errors.InvalidArgument):
        Settings.get_profile('nonsense')


def test_define_setting_then_loading_profile():
    x = Settings()
    Settings.define_setting(
        u'fun_times',
        default=3, description=u'Something something spoon',
        options=(1, 2, 3, 4),
    )
    Settings.register_profile('hi', Settings(fun_times=2))
    assert x.fun_times == 3
    assert Settings.get_profile('hi').fun_times == 2
