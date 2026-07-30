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

from hypothesis.utils.terminal import guess_background_color


@pytest.mark.parametrize(
    "env, expected",
    [
        ({"DJANGO_COLORS": "light"}, "light"),
        ({"DJANGO_COLORS": "dark;nocolor"}, "dark"),
        ({"COLORFGBG": "15;0"}, "dark"),
        ({"COLORFGBG": "7;0"}, "dark"),
        ({"COLORFGBG": "0;default;15"}, "light"),
        ({"COLORFGBG": "3;4"}, "unknown"),
        ({"COLORFGBG": "no-semicolons"}, "unknown"),
        ({}, "unknown"),
    ],
)
def test_guess_background_color(monkeypatch, env, expected):
    for var in ("DJANGO_COLORS", "COLORFGBG"):
        monkeypatch.delenv(var, raising=False)
    for var, value in env.items():
        monkeypatch.setenv(var, value)
    assert guess_background_color() == expected
