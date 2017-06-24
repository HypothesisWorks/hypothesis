# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

from unittest import TestCase

from hypothesis import given
from hypothesis.extra.django.models import emails, domains


class TestBasicValidation(TestCase):

    @given(domains)
    def test_is_never_bare_tld(self, d):
        assert '.' in d

    @given(emails)
    def test_is_valid_email(self, e):
        assert e[e.find('@')+1:].find('.') > 0
