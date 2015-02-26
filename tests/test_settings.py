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
import hypothesis.settings as hs

hs.define_setting(
    'a_setting_just_for_these_tests',
    default=3,
    description='This is a setting just for these tests'
)


def setup_function(fn):
    try:
        delattr(hs.default, 'a_setting_just_for_these_tests')
    except AttributeError:
        pass


def test_settings_uses_defaults():
    s = hs.Settings()
    assert s.a_setting_just_for_these_tests == 3


def test_picks_up_changes_to_defaults():
    hs.default.a_setting_just_for_these_tests = 18
    s = hs.Settings()
    assert s.a_setting_just_for_these_tests == 18


def test_does_not_pick_up_changes_after_instantiation():
    s = hs.Settings()
    hs.default.a_setting_just_for_these_tests = 18
    assert s.a_setting_just_for_these_tests == 3


def test_settings_repr_only_has_changes_from_defaults():
    s = hs.Settings()
    assert repr(s) == 'Settings()'
    s.a_setting_just_for_these_tests = 4
    assert repr(s) == 'Settings(a_setting_just_for_these_tests=4)'


def test_settings_repr_is_sorted():
    s = hs.Settings(
        a_setting_just_for_these_tests=10,
        min_satisfying_examples=1,
        max_examples=10,
    )
    assert repr(s) == (
        'Settings(a_setting_just_for_these_tests=10, max_examples=10, '
        'min_satisfying_examples=1)')


def test_raises_attribute_error():
    with pytest.raises(AttributeError):
        hs.Settings().kittens
