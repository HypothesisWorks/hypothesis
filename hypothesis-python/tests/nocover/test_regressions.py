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
from hypothesis._settings import note_deprecation
from hypothesis.errors import HypothesisDeprecationWarning


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


# if this test ever fails with a flaky error, #3926 has regressed.
@given(
    st.lists(
        st.floats(allow_infinity=False),
        unique=True,
    )
)
def test_unique_floats_with_nan_is_not_flaky_3926(ls):
    pass
