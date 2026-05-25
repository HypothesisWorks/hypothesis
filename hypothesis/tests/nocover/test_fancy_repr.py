# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import strategies as st


def test_floats_is_floats():
    assert repr(st.floats()) == "floats()"


def test_includes_non_default_values():
    assert repr(st.floats(max_value=1.0)) == "floats(max_value=1.0)"


def foo(*args, **kwargs):
    pass


# fmt: off
# The linebreaks here can force our lambda repr code into specific paths,
# so we tell Black to leave them as-is.


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
