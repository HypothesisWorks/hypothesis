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

import pytest

import hypothesis.strategies as st
from hypothesis import given, Phase, example, settings
from hypothesis.errors import InvalidArgument


@example(11)
@settings(phases=(Phase.explicit,))
@given(st.integers())
def test_only_runs_explicit_examples(i):
    assert i == 11


@example(u"hello world")
@settings(phases=(Phase.reuse, Phase.generate, Phase.shrink))
@given(st.booleans())
def test_does_not_use_explicit_examples(i):
    assert isinstance(i, bool)


@settings(phases=(Phase.reuse, Phase.shrink))
@given(st.booleans())
def test_this_would_fail_if_you_ran_it(b):
    assert False


def test_phases_default_to_all():
    assert settings(phases=None).phases == tuple(Phase)


def test_rejects_non_phases():
    with pytest.raises(InvalidArgument):
        settings(phases=['cabbage'])
