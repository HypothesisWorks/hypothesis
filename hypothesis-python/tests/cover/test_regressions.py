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

import pytest

from hypothesis import Verbosity, given, settings
from hypothesis import strategies as st


def strat():
    return st.builds(dict, one=strat_one())


@st.composite
def strat_one(draw):
    return draw(st.builds(dict, val=st.builds(dict, two=strat_two())))


@st.composite
def strat_two(draw):
    return draw(st.builds(dict, some_text=st.text(min_size=1)))


@given(strat())
def test_issue751(v):
    pass


def test_can_find_non_zero():
    # This future proofs against a possible failure mode where the depth bound
    # is triggered but we've fixed the behaviour of min_size so that it can
    # handle that: We want to make sure that we're really not depth bounding
    # the text in the leaf nodes.

    @settings(verbosity=Verbosity.quiet)
    @given(strat())
    def test(v):
        assert '0' in v['one']['val']['two']['some_text']

    with pytest.raises(AssertionError):
        test()


def test_mock_injection():
    """Ensure that it's possible for mechanisms like `pytest.fixture` and
    `patch` to inject mocks into hypothesis test functions without side
    effects.

    (covers https://github.com/HypothesisWorks/hypothesis-
    python/issues/491)
    """
    from mock import Mock

    class Bar():
        pass

    @given(inp=st.integers())
    def test_foo_spec(bar, inp):
        pass

    test_foo_spec(Bar())
    test_foo_spec(Mock(Bar))
    test_foo_spec(Mock())
