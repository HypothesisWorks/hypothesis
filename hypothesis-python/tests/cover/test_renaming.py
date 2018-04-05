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

from __future__ import division, print_function, absolute_import

import inspect

from tests.common.utils import checks_deprecated_behaviour
from hypothesis.internal.renaming import renamed_arguments


@renamed_arguments(old_arg='new_arg')
def f(new_arg=None, old_arg=None):
    return new_arg


def test_using_new_args():
    new_arg = 'A number of numbats at night'
    assert f(new_arg=new_arg) == new_arg
    assert f.__doc__ is None


@checks_deprecated_behaviour
def test_using_old_args():
    old_arg = 'An order of otters on the Ouse'
    assert f(old_arg=old_arg) == old_arg
    assert f.__doc__ is None


@renamed_arguments(old_arg='new_arg')
def g(new_arg=None, old_arg=None):
    """Hi.

    Bye
    """


def test_docstring():
    """Make sure the docstring's indentation didn't get messed up."""
    assert inspect.cleandoc(g.__doc__).startswith('Hi.\n\nBye')
