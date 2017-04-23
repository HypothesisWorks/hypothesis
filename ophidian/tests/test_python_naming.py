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

import pytest

from ophidian.finder import is_valid_python_name


@pytest.mark.parametrize(
    'name', [
        'python',
        'pypy',
        'python2',
        'python2.7',
        'python2.7.1',
        'python3.7.1',
    ]
)
def test_valid_names(name):
    assert is_valid_python_name(name)


@pytest.mark.parametrize(
    'name', [
        'python-',
        'python.',
        'python..exe',
        'python2..7',
    ]
)
def test_invalid_names(name):
    assert not is_valid_python_name(name)
