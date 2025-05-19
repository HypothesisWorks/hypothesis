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

from hypothesis import given, settings, strategies as st
from hypothesis._settings import note_deprecation
from hypothesis.errors import HypothesisDeprecationWarning

from tests.common.utils import Why, xfail_on_crosshair


def test_note_deprecation_blames_right_code_issue_652():
    msg = "this is an arbitrary deprecation warning message"

    @st.composite
    def deprecated_strategy(draw):
        draw(st.none())
        note_deprecation(msg, since="RELEASEDAY", has_codemod=False)

    @given(deprecated_strategy())
    def f(x):
        pass

    with pytest.warns(HypothesisDeprecationWarning) as log:
        f()

    assert len(log) == 1
    (record,) = log
    # We got the warning we expected, from the right file
    assert isinstance(record.message, HypothesisDeprecationWarning)
    assert record.message.args == (msg,)
    assert record.filename == __file__


@given(
    x=st.one_of(st.just(0) | st.just(1)),
    y=st.one_of(st.just(0) | st.just(1) | st.just(2)),
)
def test_performance_issue_2027(x, y):
    pass


@given(
    st.lists(
        st.floats(allow_infinity=False),
        unique=True,
    )
)
def test_unique_floats_with_nan_is_not_flaky_3926(ls):
    pass


# this will take a while to find the regression, but will eventually trigger it.
# min_value=0 is critical to trigger the probing behavior which exhausts our buffer.
# https://github.com/pschanely/CrossHair/issues/285 for an upstream fix.
@xfail_on_crosshair(Why.other, strict=False)
@given(st.integers(min_value=0, max_value=1 << 25_000))
def test_overrun_during_datatree_simulation_3874(n):
    pass


def test_explain_phase_label_assertion_4339():
    # st.composite causes a re-creation of the SampledFromStrategy each time
    # (one_of is implemented using sampled_from internally), which previously
    # had different labels which triggered an assertion in the explain code.
    @st.composite
    def g(draw):
        draw(st.none() | st.booleans())

    @given(g(), st.none() | st.booleans())
    @settings(database=None)
    def f(a, b):
        raise ValueError("marker")

    with pytest.raises(ValueError, match="marker"):
        f()
