# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis.utils.dynamicvariables import DynamicVariable


def test_can_assign():
    d = DynamicVariable(1)
    assert d.value == 1
    with d.with_value(2):
        assert d.value == 2
    assert d.value == 1


def test_can_nest():
    d = DynamicVariable(1)
    with d.with_value(2):
        assert d.value == 2
        with d.with_value(3):
            assert d.value == 3
        assert d.value == 2
    assert d.value == 1
