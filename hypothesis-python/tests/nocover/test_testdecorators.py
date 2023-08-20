# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import re

import pytest

from hypothesis import HealthCheck, given, reject, settings, strategies as st
from hypothesis.errors import InvalidArgument, Unsatisfiable


def test_contains_the_test_function_name_in_the_exception_string():
    look_for_one = settings(max_examples=1, suppress_health_check=list(HealthCheck))

    @given(st.integers())
    @look_for_one
    def this_has_a_totally_unique_name(x):
        reject()

    with pytest.raises(
        Unsatisfiable, match=re.escape(this_has_a_totally_unique_name.__name__)
    ):
        this_has_a_totally_unique_name()

    class Foo:
        @given(st.integers())
        @look_for_one
        def this_has_a_unique_name_and_lives_on_a_class(self, x):
            reject()

    with pytest.raises(
        Unsatisfiable,
        match=re.escape(Foo.this_has_a_unique_name_and_lives_on_a_class.__name__),
    ):
        Foo().this_has_a_unique_name_and_lives_on_a_class()


def test_signature_mismatch_error_message():
    # Regression test for issue #1978

    @settings(max_examples=2)
    @given(x=st.integers())
    def bad_test():
        pass

    with pytest.raises(
        InvalidArgument,
        match=r"bad_test\(\) got an unexpected keyword argument 'x', "
        r"from `x=integers\(\)` in @given",
    ):
        bad_test()


@given(data=st.data(), keys=st.lists(st.integers(), unique=True))
def test_fixed_dict_preserves_iteration_order(data, keys):
    d = data.draw(st.fixed_dictionaries({k: st.none() for k in keys}))
    assert all(a == b for a, b in zip(keys, d)), f"keys={keys}, d.keys()={d.keys()}"
