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

from hypothesis import strategies as st
from hypothesis.errors import InvalidArgument


def test_no_args():
    assert st.text() is st.text()


def test_tuple_lengths():
    assert st.tuples(st.integers()) is st.tuples(st.integers())
    assert st.tuples(st.integers()) is not st.tuples(st.integers(), st.integers())


def test_values():
    assert st.integers() is not st.integers(min_value=1)


def test_alphabet_key():
    assert st.text(alphabet="abcs") is st.text(alphabet="abcs")


def test_does_not_error_on_unhashable_posarg():
    st.text(["a", "b", "c"])


def test_does_not_error_on_unhashable_kwarg():
    with pytest.raises(InvalidArgument):
        st.builds(lambda alphabet: 1, alphabet=["a", "b", "c"]).validate()


def test_caches_floats_sensitively():
    assert st.floats(min_value=0.0) is st.floats(min_value=0.0)
    assert st.floats(min_value=0.0) is not st.floats(min_value=0)
    assert st.floats(min_value=0.0) is not st.floats(min_value=-0.0)
