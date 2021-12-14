# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from importlib.metadata import EntryPoint, entry_points  # type: ignore
from typing import Dict
from warnings import catch_warnings

import pytest

from hypothesis.errors import HypothesisWarning
from hypothesis.extra.array_api import make_strategies_namespace, mock_xp
from hypothesis.internal.floats import next_up

__all__ = [
    "xp",
    "xps",
    "COMPLIANT_XP",
    "WIDTHS_FTZ",
]


def installed_array_modules() -> Dict[str, EntryPoint]:
    """Returns a dictionary of array module names paired to their entry points

    A convenience wrapper for importlib.metadata.entry_points(). It has the
    added benefit of working with both the original dict interface and the new
    select interface, so this can be used warning-free in all modern Python
    versions.
    """
    try:
        eps = entry_points(group="array_api")
    except TypeError:
        # The select interface for entry_points was introduced in py3.10,
        # supplanting its dict interface. We fallback to the dict interface so
        # we can still find entry points in py3.8 and py3.9.
        eps = entry_points().get("array_api", [])
    return {ep.name: ep for ep in eps}


# We try importing the Array API namespace from NumPy first, which modern
# versions should include. If not available we default to our own mocked module,
# which should allow our test suite to still work. A constant is set accordingly
# to inform our test suite of whether the array module here is a mock or not.
modules = installed_array_modules()
try:
    with catch_warnings():  # NumPy currently warns on import
        xp = modules["numpy"].load()
except KeyError:
    xp = mock_xp
    with pytest.warns(HypothesisWarning):
        xps = make_strategies_namespace(xp)
    COMPLIANT_XP = False
else:
    xps = make_strategies_namespace(xp)
    COMPLIANT_XP = True

# Infer whether build of array module has its float flush subnormals to zero
WIDTHS_FTZ = {
    32: bool(xp.asarray(next_up(0.0, width=32), dtype=xp.float32) == 0),
    64: bool(xp.asarray(next_up(0.0, width=64), dtype=xp.float64) == 0),
}
