# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, unicode_literals

from hypothesis import given, falsify
from hypothesis.extra.fakefactory import FakeFactory


@given(FakeFactory('email'))
def test_email(email):
    assert '@' in email


@given(FakeFactory('name', locale='en_US'))
def test_english_names_are_ascii(name):
    name.encode('ascii')


def test_french_names_may_have_an_accent():
    falsify(
        lambda x: 'é' not in x,
        FakeFactory('name', locale='fr_FR')
    )
