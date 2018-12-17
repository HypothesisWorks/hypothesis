# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

from __future__ import absolute_import, division, print_function

import pytest

from hypothesis import given
from hypothesis.errors import InvalidArgument
from hypothesis.internal.reflection import get_pretty_function_description
from hypothesis.strategies import integers

# fmt: off


def test_destructuring_lambdas():
    assert get_pretty_function_description(lambda (x, y): 1) == \
        u'lambda (x, y): <unknown>'


def test_destructuring_not_allowed():
    @given(integers())
    def foo(a, (b, c)):
        pass
    with pytest.raises(InvalidArgument):
        foo()
