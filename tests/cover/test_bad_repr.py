# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

import hypothesis.strategies as st
from hypothesis import given
from hypothesis.internal.compat import unicode_safe_repr
from hypothesis.internal.reflection import arg_string


class BadRepr(object):

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return self.value


Frosty = BadRepr(u'☃')


def test_just_frosty():
    assert unicode_safe_repr(st.just(Frosty)) == u'just(☃)'


def test_sampling_snowmen():
    assert unicode_safe_repr(st.sampled_from((
        Frosty, u'hi'))) == u'sampled_from((☃, %s))' % (repr(u'hi'),)


def varargs(*args, **kwargs):
    pass


def test_arg_strings_are_bad_repr_safe():
    assert arg_string(varargs, (Frosty,), {}) == u'☃'
    assert arg_string(varargs, (), {u'x': Frosty}) == u'x=☃'


@given(st.sampled_from([
    u'✐', u'✑', u'✒', u'✓', u'✔', u'✕', u'✖', u'✗', u'✘',
    u'✙', u'✚', u'✛', u'✜', u'✝', u'✞', u'✟', u'✠', u'✡', u'✢', u'✣']))
def test_sampled_from_bad_repr(c):
    pass
