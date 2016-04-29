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

# most interesting tests of this nature are exected in nocover, but we have
# a few here to make sure we have coverage of the strategytests module itself.


from __future__ import division, print_function, absolute_import

from hypothesis.strategies import sets, booleans, integers
from hypothesis.strategytests import strategy_test_suite

TestBoolSets = strategy_test_suite(sets(booleans()))
TestInts = strategy_test_suite(integers())
