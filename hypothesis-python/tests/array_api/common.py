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
from typing import Literal

import pytest

from hypothesis.extra.array_api import (
    COMPLEX_NAMES,
    REAL_NAMES,
    RELEASED_VERSIONS,
    NominalVersion,
)
from hypothesis.internal.floats import next_up

__all__ = [
    "MIN_VER_FOR_COMPLEX",
    "dtype_name_params",
    "flushes_to_zero",
    "installed_array_modules",
]


MIN_VER_FOR_COMPLEX: NominalVersion = "2022.12"
if len(RELEASED_VERSIONS) > 1:
    assert MIN_VER_FOR_COMPLEX == RELEASED_VERSIONS[1]


def installed_array_modules() -> dict[str, EntryPoint]:
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
        # we can still find entry points in py3.9.
        eps = entry_points().get("array_api", [])
    return {ep.name: ep for ep in eps}


def flushes_to_zero(xp, width: Literal[32, 64]) -> bool:
    """Infer whether build of array module has its float dtype of the specified
    width flush subnormals to zero

    We do this per-width because compilers might FTZ for one dtype but allow
    subnormals in the other.
    """
    if width not in [32, 64]:
        raise ValueError(f"{width=}, but should be either 32 or 64")
    dtype = getattr(xp, f"float{width}")
    return bool(xp.asarray(next_up(0.0, width=width), dtype=dtype) == 0)


dtype_name_params = ["bool", *REAL_NAMES]
for name in COMPLEX_NAMES:
    param = pytest.param(name, marks=pytest.mark.xp_min_version(MIN_VER_FOR_COMPLEX))
    dtype_name_params.append(param)
