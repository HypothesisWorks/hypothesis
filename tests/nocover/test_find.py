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

import pytest

from hypothesis import find, settings as Settings
from hypothesis.errors import NoSuchExample
from hypothesis.strategies import booleans, dictionaries, floats, integers, lists

from tests.common.debug import minimal


def test_can_find_an_int():
    assert minimal(integers()) == 0
    assert minimal(integers(), lambda x: x >= 13) == 13


def test_can_find_list():
    x = minimal(lists(integers()), lambda x: sum(x) >= 10)
    assert sum(x) == 10


def test_can_find_nan():
    minimal(floats(), math.isnan)


def test_can_find_nans():
    x = minimal(lists(floats()), lambda x: math.isnan(sum(x)))
    if len(x) == 1:
        assert math.isnan(x[0])
    else:
        assert 2 <= len(x) <= 3


def test_condition_is_name():
    settings = Settings(max_examples=20)
    with pytest.raises(NoSuchExample) as e:
        find(booleans(), lambda x: False, settings=settings)
    assert "lambda x:" in e.value.args[0]

    with pytest.raises(NoSuchExample) as e:
        find(integers(), lambda x: "☃" in str(x), settings=settings)
    assert "lambda x:" in e.value.args[0]

    def bad(x):
        return False

    with pytest.raises(NoSuchExample) as e:
        find(integers(), bad, settings=settings)
    assert "bad" in e.value.args[0]


def test_find_dictionary():
    smallest = minimal(
        dictionaries(keys=integers(), values=integers()),
        lambda xs: any(kv[0] > kv[1] for kv in xs.items()),
    )
    assert len(smallest) == 1
