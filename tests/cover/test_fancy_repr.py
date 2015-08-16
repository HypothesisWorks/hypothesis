# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

import hypothesis.strategies as st


def test_floats_is_floats():
    assert repr(st.floats()) == 'floats()'


def test_includes_non_default_values():
    assert repr(st.floats(max_value=1.0)) == 'floats(max_value=1.0)'


def foo(*args, **kwargs):
    pass


def test_builds_repr():
    assert repr(st.builds(foo, st.just(1), x=st.just(10))) == \
        'builds(foo, just(1), x=just(10))'


def test_map_repr():
    assert repr(st.integers().map(abs)) == 'integers().map(abs)'
    assert repr(st.integers().map(lambda x: x * 2)) == \
        'integers().map(lambda x: x * 2)'


def test_filter_repr():
    assert repr(st.integers().filter(lambda x: x != 3)) == \
        'integers().filter(lambda x: x != 3)'


def test_flatmap_repr():
    assert repr(st.integers().flatmap(lambda x: st.booleans())) == \
        'integers().flatmap(lambda x: st.booleans())'
