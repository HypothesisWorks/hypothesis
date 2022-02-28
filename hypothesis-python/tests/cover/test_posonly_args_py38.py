# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from hypothesis import given, strategies as st


@st.composite
def strat(draw, x=0, /):
    return draw(st.integers(min_value=x))


@given(st.data(), st.integers())
def test_composite_with_posonly_args(data, min_value):
    v = data.draw(strat(min_value))
    assert min_value <= v


def test_preserves_signature():
    with pytest.raises(TypeError):
        strat(x=1)


def test_builds_real_pos_only():
    with pytest.raises(TypeError):
        st.builds()  # requires a target!
