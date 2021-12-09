# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from warnings import catch_warnings

import pytest

from hypothesis.errors import HypothesisWarning
from hypothesis.extra.array_api import (
    installed_array_modules,
    make_strategies_namespace,
    mock_xp,
)
from hypothesis.internal.floats import next_up

__all__ = [
    "xp",
    "xps",
    "COMPLIANT_XP",
    "WIDTHS_FTZ",
]


# We try importing the Array API namespace from NumPy first, which modern
# versions should include. If not available we default to our own mocked module,
# which should allow our test suite to still work. A constant is set accordingly
# to inform our test suite of whether the array module here is a mock or not.
try:
    with catch_warnings():  # libraries might warn on importing their namespace
        modules = installed_array_modules()
    xp = modules["numpy"]
    xps = make_strategies_namespace(xp)
    COMPLIANT_XP = True
except KeyError:
    xp = mock_xp
    with pytest.warns(HypothesisWarning):
        xps = make_strategies_namespace(xp)
    COMPLIANT_XP = False

# Infer whether build of array module has its float flush subnormals to zero
WIDTHS_FTZ = {
    32: bool(xp.asarray(next_up(0.0, width=32), dtype=xp.float32) == 0),
    64: bool(xp.asarray(next_up(0.0, width=64), dtype=xp.float64) == 0),
}
