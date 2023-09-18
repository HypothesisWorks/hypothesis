# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import given, strategies as st

from tests.conjecture.test_inquisitor import fails_with_output


@fails_with_output(
    """
Falsifying example: test_inquisitor_tuple(
    abc=(
        '',  # or any other generated value
        '',  # or any other generated value
        '',  # or any other generated value
    )
)
# The test sometimes passed when commented parts were varied together.
"""
)
@given(st.tuples(st.text(), st.text(), st.text()))
def test_inquisitor_tuple(abc):
    assert all(abc)


@fails_with_output(
    """
Falsifying example: test_inquisitor_fixeddict(
    abc={
        'a': '',  # or any other generated value
        'b': '',  # or any other generated value
        'c': '',  # or any other generated value
    }
)
# The test sometimes passed when commented parts were varied together.
"""
)
@given(st.fixed_dictionaries({"a": st.text(), "b": st.text(), "c": st.text()}))
def test_inquisitor_fixeddict(abc):
    assert all(abc.values())


def fn(*args, **kwargs):
    return [*args, *kwargs.values()]


@fails_with_output(
    """
Falsifying example: test_inquisitor_builds(
    abc=fn(
        '',  # or any other generated value
        b='',  # or any other generated value
        c='',  # or any other generated value
    )
)
# The test sometimes passed when commented parts were varied together.
"""
)
@given(st.builds(fn, st.text(), b=st.text(), c=st.text()))
def test_inquisitor_builds(abc):
    assert all(abc)
