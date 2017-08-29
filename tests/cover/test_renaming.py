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

from hypothesis.internal.renaming import renamed_arguments


def test_can_rename_arguments_in_a_function_with_no_docstring():
    @renamed_arguments(old_arg='new_arg')
    def f(new_arg=None, old_arg=None):
        return new_arg

    new_arg = 'Hello world'
    assert f(old_arg=new_arg) == new_arg
    assert f(new_arg=new_arg) == new_arg
    assert f.__doc__ is None
