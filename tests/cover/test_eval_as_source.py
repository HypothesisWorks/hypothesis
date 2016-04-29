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

from hypothesis.internal.reflection import source_exec_as_module


def test_can_eval_as_source():
    assert source_exec_as_module('foo=1').foo == 1


def test_caches():
    x = source_exec_as_module('foo=2')
    y = source_exec_as_module('foo=2')
    assert x is y


RECURSIVE = """
from hypothesis.internal.reflection import source_exec_as_module

def test_recurse():
    assert not (
        source_exec_as_module("too_much_recursion = False").too_much_recursion)
"""


def test_can_call_self_recursively():
    source_exec_as_module(RECURSIVE).test_recurse()
