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

import warnings

import pytest

import hypothesis.strategies as st
from hypothesis import given, settings
from hypothesis.errors import HypothesisDeprecationWarning
from hypothesis.internal.compat import PY3
from hypothesis.internal.reflection import arg_string

original_profile = settings.default

settings.register_profile(
    'nonstrict', settings(strict=False)
)


def setup_function(fn):
    settings.load_profile('nonstrict')
    warnings.simplefilter('always', HypothesisDeprecationWarning)


def teardown_function(fn):
    settings.load_profile('default')
    warnings.simplefilter('once', HypothesisDeprecationWarning)


class BadRepr(object):

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return self.value


Frosty = BadRepr('☃')


def test_just_frosty():
    assert repr(st.just(Frosty)) == 'just(☃)'


def test_sampling_snowmen():
    assert repr(st.sampled_from((
        Frosty, 'hi'))) == 'sampled_from((☃, %s))' % (repr('hi'),)


def varargs(*args, **kwargs):
    pass


@pytest.mark.skipif(PY3, reason='Unicode repr is kosher on python 3')
def test_arg_strings_are_bad_repr_safe():
    assert arg_string(varargs, (Frosty,), {}) == '☃'


@pytest.mark.skipif(PY3, reason='Unicode repr is kosher on python 3')
def test_arg_string_kwargs_are_bad_repr_safe():
    assert arg_string(varargs, (), {'x': Frosty}) == 'x=☃'


@given(st.sampled_from([
    '✐', '✑', '✒', '✓', '✔', '✕', '✖', '✗', '✘',
    '✙', '✚', '✛', '✜', '✝', '✞', '✟', '✠', '✡', '✢', '✣']))
def test_sampled_from_bad_repr(c):
    pass
