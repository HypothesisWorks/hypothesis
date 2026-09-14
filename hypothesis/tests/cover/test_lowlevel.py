# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import math
import re
from random import Random

import pytest

from hypothesis import HealthCheck, given, settings, strategies as st
from hypothesis.errors import CannotInvert, InvalidArgument
from hypothesis.internal.conjecture.data import ConjectureData, Status, StopTest
from hypothesis.lowlevel import many, weighted_booleans
from hypothesis.lowlevel.lowlevel import _ONE_FROM_MANY_LABEL

from tests.common.debug import (
    assert_all_examples,
    check_can_generate_examples,
    find_any,
    minimal,
)


@pytest.mark.parametrize("p", [-0.1, 1.1, math.nan, math.inf, "0.5"])
def test_weighted_booleans_invalid_argument(p):
    with pytest.raises(InvalidArgument):
        weighted_booleans(p=p)


def test_weighted_booleans_repr():
    assert repr(weighted_booleans(p=0.25)) == "weighted_booleans(p=0.25)"


def test_weighted_booleans_p_zero_and_one_are_constant():
    assert_all_examples(weighted_booleans(p=0), lambda x: x is False)
    assert_all_examples(weighted_booleans(p=1), lambda x: x is True)


def test_weighted_booleans_generates_both_values():
    find_any(weighted_booleans(p=0.9), lambda x: x is True)
    find_any(weighted_booleans(p=0.9), lambda x: x is False)


def test_weighted_booleans_shrinks_towards_false():
    assert minimal(weighted_booleans(p=0.99)) is False


@given(st.floats(0, 1))
def test_weighted_booleans_inverts_permitted_values(p):
    strategy = weighted_booleans(p=p)
    for value in [False, True]:
        if (value and p == 0) or (not value and p == 1):
            with pytest.raises(CannotInvert):
                strategy._invert(value)
        else:
            assert strategy._invert(value) == (value,)


def test_weighted_booleans_inverts_only_bools():
    with pytest.raises(CannotInvert):
        weighted_booleans(p=0.5)._invert(1)


@given(st.data())
def test_many_at_test_level(data):
    count = 0
    for _ in many(max_size=5):
        data.draw(st.integers())
        count += 1
    assert count <= 5


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_size": -1},
        {"min_size": "1"},
        {"max_size": -1},
        {"max_size": 1.5},
        {"min_size": 3, "max_size": 2},
        {"average_size": 2, "max_size": 1},
        {"min_size": 3, "average_size": 2},
        {"min_size": 1, "max_size": 5, "average_size": 1},
        {"min_size": 0, "max_size": 5, "average_size": 5},
        {"min_size": 0, "average_size": math.inf},
    ],
)
def test_many_validates_sizes(kwargs):
    with pytest.raises(InvalidArgument):
        many(**kwargs)


def test_many_fixed_size_accepts_equal_average_size():
    count, _ = run_many((), min_size=3, max_size=3, average_size=3)
    assert count == 3


def test_many_default_average_size_is_valid():
    check_can_generate_examples(st.lists(st.integers(), min_size=10, max_size=10_000))


def run_many(choices, **kwargs):
    data = ConjectureData.for_choices(choices)
    count = sum(1 for _ in many(_data=data, **kwargs))
    return count, data


def test_many_fixed_size_draws_no_booleans():
    count, data = run_many((), min_size=3, max_size=3)
    assert count == 3
    assert data.choices == ()


def test_many_astronomically_unlikely_average_size():
    # p_continue doesn't underflow to zero, so continuing is still permitted
    # even though we'd never generate an element for such a low average size.
    count, _ = run_many((True,) * 1000, min_size=0, max_size=10, average_size=1e-5)
    assert count == 10


def test_many_with_min_size():
    count, _ = run_many((False,) * 5, min_size=2, max_size=1000, average_size=10)
    assert count == 2


def test_many_with_max_size():
    count, _ = run_many((True,) * 5, min_size=0, max_size=2, average_size=1)
    assert count == 2


def test_rejection_eventually_terminates_many():
    data = ConjectureData.for_choices((True,) * 1000)
    count = 0
    for reject in many(min_size=0, max_size=1000, average_size=100, _data=data):
        count += 1
        reject()
    assert count <= 100


def test_rejection_below_min_size_abandons_the_test_case():
    data = ConjectureData.for_choices((True,) * 1000)
    with pytest.raises(StopTest):
        for reject in many(min_size=1, max_size=1000, _data=data):
            reject("no good")
    assert data.status == Status.INVALID
    assert data.events["gave up because"] == "no good"


def test_rejected_element_span_is_discarded():
    data = ConjectureData.for_choices([True, 0, True, 1, False])
    for reject in many(min_size=0, max_size=10, average_size=5, _data=data):
        if data.draw_integer(0, 10) == 0:
            reject()

    data.freeze()
    discards = [
        span.discarded for span in data.spans if span.label == _ONE_FROM_MANY_LABEL
    ]
    # the rejected first element is discarded; the second and the final
    # stop-drawing span are not.
    assert discards == [True, False, False]


def test_many_finish():
    data = ConjectureData.for_choices((True,) * 10)
    elements = many(min_size=0, max_size=10, _data=data)
    for _ in elements:
        elements.finish()
    assert data.choices == (True, False)


def test_finish_overrides_min_size():
    data = ConjectureData.for_choices(())
    count = 0
    elements = many(min_size=3, max_size=3, _data=data)
    for _ in elements:
        count += 1
        elements.finish()
    assert count == 1


def test_many_unobserved_records_nothing():
    data = ConjectureData(random=Random(0))
    count = sum(1 for _ in many(min_size=1, max_size=10, _data=data, _observe=False))
    assert count >= 1
    assert data.choices == ()


@settings(suppress_health_check=[HealthCheck.filter_too_much])
@given(st.data())
def test_many_public_api(data):
    # exercise all the bits of the many() public api, like a user would
    min_size = data.draw(st.integers(0, 5))
    max_size = data.draw(st.none() | st.integers(min_size, 10))
    hi = 10 if max_size is None else max_size
    average_size = data.draw(
        st.none()
        | st.floats(
            min_size, hi, exclude_min=min_size != hi, exclude_max=min_size != hi
        )
    )
    elements = many(min_size=min_size, max_size=max_size, average_size=average_size)
    if data.draw(st.booleans()):
        elements.finish()
    for reject in elements:
        for _ in range(data.draw(st.integers(0, 2))):
            data.draw(st.integers(0, 100))
        if data.draw(st.booleans()):
            reject()
        if data.draw(st.booleans()):
            elements.finish()


@given(st.data())
def test_many_choices_always_have_the_same_shape(data):
    # similar to test_many_public_api but also checks the shape of the resulting choice
    # sequence from many() is what we expect
    min_size = data.draw(st.integers(0, 5))
    max_size = data.draw(st.none() | st.integers(min_size, 10))
    hi = 10 if max_size is None else max_size
    average_size = data.draw(
        st.none()
        | st.floats(
            min_size, hi, exclude_min=min_size != hi, exclude_max=min_size != hi
        )
    )
    cd = ConjectureData(random=data.draw(st.randoms(use_true_random=True)))
    elements = many(
        min_size=min_size, max_size=max_size, average_size=average_size, _data=cd
    )
    if data.draw(st.booleans()):
        elements.finish()

    interrupted = False
    try:
        for reject in elements:
            for _ in range(data.draw(st.integers(0, 2))):
                cd.draw_integer(0, 100)
            if data.draw(st.booleans()):
                reject()
            if data.draw(st.booleans()):
                elements.finish()
    except StopTest:
        assert cd.status == Status.INVALID
        interrupted = True

    # many draws True, <element choices> per element, then False.
    # If min_size == max_size, the collection has a fixed size and draws no booleans
    # at all.
    #
    # We want to assert each many's choices has this shape. It looks weird to convert
    # it to a string, but since it's very natural to express our assertion as a regular
    # expression, this is actually pretty clean.
    shape = "".join(("T" if c else "F") if type(c) is bool else "x" for c in cd.choices)
    if min_size == max_size:
        assert "T" not in shape
        assert "F" not in shape
    else:
        assert re.fullmatch(r"(Tx*)*F" if not interrupted else r"(Tx*)*F?", shape)
