# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import warnings

import pytest

import hypothesis.strategies as st
from hypothesis import given, Settings
from hypothesis.errors import HypothesisDeprecationWarning
from hypothesis.internal.compat import PY3, unicode_safe_repr
from hypothesis.internal.reflection import arg_string

original_profile = Settings.default

Settings.register_profile(
    'nonstrict', Settings(strict=False)
)


def setup_function(fn):
    Settings.load_profile('nonstrict')
    warnings.simplefilter('always', HypothesisDeprecationWarning)


def teardown_function(fn):
    Settings.load_profile('default')
    warnings.simplefilter('once', HypothesisDeprecationWarning)


class BadRepr(object):

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return self.value


Frosty = BadRepr(u'☃')


@pytest.mark.skipif(PY3, reason='Unicode repr is kosher on python 3')
def test_just_frosty():
    with pytest.warns(HypothesisDeprecationWarning):
        assert unicode_safe_repr(st.just(Frosty)) == u'just(☃)'


@pytest.mark.skipif(PY3, reason='Unicode repr is kosher on python 3')
def test_sampling_snowmen():
    with pytest.warns(HypothesisDeprecationWarning):
        assert unicode_safe_repr(st.sampled_from((
            Frosty, u'hi'))) == u'sampled_from((☃, %s))' % (repr(u'hi'),)


def varargs(*args, **kwargs):
    pass


@pytest.mark.skipif(PY3, reason='Unicode repr is kosher on python 3')
def test_arg_strings_are_bad_repr_safe():
    with pytest.warns(HypothesisDeprecationWarning):
        assert arg_string(varargs, (Frosty,), {}) == u'☃'


@pytest.mark.skipif(PY3, reason='Unicode repr is kosher on python 3')
def test_arg_string_kwargs_are_bad_repr_safe():
    with pytest.warns(HypothesisDeprecationWarning):
        assert arg_string(varargs, (), {u'x': Frosty}) == u'x=☃'


@given(st.sampled_from([
    u'✐', u'✑', u'✒', u'✓', u'✔', u'✕', u'✖', u'✗', u'✘',
    u'✙', u'✚', u'✛', u'✜', u'✝', u'✞', u'✟', u'✠', u'✡', u'✢', u'✣']))
def test_sampled_from_bad_repr(c):
    pass
