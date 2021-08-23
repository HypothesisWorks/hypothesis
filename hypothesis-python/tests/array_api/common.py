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

import pytest

from hypothesis.errors import HypothesisWarning
from hypothesis.extra.array_api import make_strategies_namespace, mock_xp

__all__ = [
    "xp",
    "xps",
    "MOCK_WARN_MSG",
    "COMPLIANT_XP",
]


MOCK_WARN_MSG = f"determine.*{mock_xp.__name__}.*Array API"

# We try importing the Array API namespace from NumPy first, which modern
# versions should include. If not available we default to our own mocked module,
# which should allow our test suite to still work. A constant is set accordingly
# to inform our test suite of whether the array module here is a mock or not.
try:
    with pytest.warns(UserWarning):
        from numpy import array_api as xp  # type: ignore
    xps = make_strategies_namespace(xp)
    COMPLIANT_XP = True
except ImportError:
    xp = mock_xp
    with pytest.warns(HypothesisWarning):
        xps = make_strategies_namespace(xp)
    COMPLIANT_XP = False
