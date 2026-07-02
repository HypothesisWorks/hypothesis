# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from enum import Flag, auto

from hypothesis import given, strategies as st

from tests.common.utils import SNAPSHOT_SETTINGS, run_test_for_falsifying_example


class Direction(Flag):
    NORTH = auto()
    SOUTH = auto()
    EAST = auto()
    WEST = auto()


def test_data_draw(snapshot):
    @SNAPSHOT_SETTINGS
    @given(data=st.data())
    def inner(data):
        data.draw(st.integers())
        data.draw(st.text(max_size=3))
        raise AssertionError

    assert run_test_for_falsifying_example(inner) == snapshot


def test_sampled_from_enum_flag(snapshot):
    class Color(Flag):
        RED = auto()
        GREEN = auto()
        BLUE = auto()

    @SNAPSHOT_SETTINGS
    @given(c=st.sampled_from(Color))
    def inner(c):
        assert not (c & Color.RED)

    assert run_test_for_falsifying_example(inner) == snapshot


def test_sampled_from_module_level_enum_flag(snapshot):
    @SNAPSHOT_SETTINGS
    @given(d=st.sampled_from(Direction))
    def inner(d):
        assert not (d & Direction.NORTH)

    assert run_test_for_falsifying_example(inner) == snapshot
