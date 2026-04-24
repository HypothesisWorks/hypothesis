# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Snapshot tests pinning the ``DataObject(draws=[...])`` rendering that
Hypothesis produces in the falsifying example for ``st.data()``-driven
tests. See the ``snapshot_given`` helper for the shape of each test."""

import functools
import inspect

from hypothesis import given, strategies as st

from tests.common.utils import run_test_for_falsifying_example
from tests.snapshots.conftest import EXPLAIN_SETTINGS


def snapshot_given(*strategies, **kwarg_strategies):
    """Decorator that turns the wrapped body into a pytest test: runs it as
    a Hypothesis property test (always forcing a failure) and asserts that
    the captured falsifying-example output equals the ``snapshot`` fixture
    value."""

    def decorator(body):
        @functools.wraps(body)
        def prop_body(*args, **kwargs):
            body(*args, **kwargs)

        prop_body.__signature__ = inspect.signature(body)
        prop_test = given(*strategies, **kwarg_strategies)(EXPLAIN_SETTINGS(prop_body))

        def test_function(snapshot):
            assert run_test_for_falsifying_example(prop_test) == snapshot

        test_function.__name__ = body.__name__
        test_function.__qualname__ = body.__qualname__
        return test_function

    return decorator


@snapshot_given(st.data())
def test_snapshot_no_draws(data):
    raise AssertionError


@snapshot_given(st.data())
def test_snapshot_single_draw(data):
    data.draw(st.integers(min_value=0, max_value=10))
    raise AssertionError


@snapshot_given(st.data())
def test_snapshot_multiple_unlabeled_draws(data):
    data.draw(st.integers(min_value=0, max_value=10))
    data.draw(st.text(max_size=3))
    data.draw(st.booleans())
    raise AssertionError


@snapshot_given(st.data())
def test_snapshot_single_labeled_draw(data):
    data.draw(st.integers(min_value=0, max_value=10), label="Cool thing")
    raise AssertionError


@snapshot_given(st.data())
def test_snapshot_all_labeled_draws(data):
    data.draw(st.integers(min_value=0, max_value=10), label="first number")
    data.draw(st.integers(min_value=0, max_value=10), label="second number")
    raise AssertionError


@snapshot_given(st.data())
def test_snapshot_mixed_labeled_and_unlabeled(data):
    data.draw(st.integers(min_value=0, max_value=10))
    data.draw(st.text(max_size=3), label="middle")
    data.draw(st.booleans())
    raise AssertionError


@snapshot_given(st.data())
def test_snapshot_nested_value(data):
    data.draw(
        st.lists(st.integers(min_value=0, max_value=5), min_size=1),
        label="a list",
    )
    raise AssertionError


@snapshot_given(st.integers(min_value=0, max_value=10), st.data())
def test_snapshot_alongside_other_args(n, data):
    data.draw(st.integers(min_value=0, max_value=10), label="inner draw")
    raise AssertionError


@snapshot_given(st.data(), st.data())
def test_snapshot_two_data_args(d1, d2):
    d1.draw(st.integers(min_value=0, max_value=10), label="from d1")
    d2.draw(st.integers(min_value=0, max_value=10))
    raise AssertionError


@snapshot_given(st.data())
def test_recursive_reference_to_data(data):
    data.draw(st.just(data))
    raise AssertionError


@snapshot_given(st.data())
def test_only_some_values_are_allowed_to_vary(data):
    data.draw(st.integers())
    n = data.draw(st.integers())
    data.draw(st.integers())

    assert n < 100


@snapshot_given(st.data())
def test_only_some_values_are_allowed_to_vary_with_labels(data):
    data.draw(st.integers(), label="a")
    n = data.draw(st.integers(), label="b")
    data.draw(st.integers(), label="c")

    assert n < 100
