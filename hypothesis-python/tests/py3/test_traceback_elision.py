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

import traceback

import pytest

import hypothesis.strategies as st
from hypothesis import Verbosity, given, settings


@pytest.mark.parametrize('verbosity', [Verbosity.normal, Verbosity.debug])
def test_tracebacks_omit_hypothesis_internals(verbosity):
    @settings(verbosity=verbosity)
    @given(st.none())
    def simplest_failure(x):
        assert x

    try:
        simplest_failure()
    except AssertionError as e:
        tb = traceback.extract_tb(e.__traceback__)
        # Unless in debug mode, Hypothesis adds 1 frame - the least possible!
        # (4 frames: this one, simplest_failure, internal frame, assert False)
        if verbosity < Verbosity.debug:
            assert len(tb) == 4
        else:
            assert len(tb) >= 5
