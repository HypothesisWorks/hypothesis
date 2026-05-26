# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import collections.abc


class CustomClass:
    def __init__(self, number: int) -> None:
        self.number = number


def add_custom_classes(c1: CustomClass, c2: CustomClass | None = None) -> CustomClass:
    if c2 is None:
        return CustomClass(c1.number)
    return CustomClass(c1.number + c2.number)


def merge_dicts(
    map1: collections.abc.Mapping[str, int], map2: collections.abc.Mapping[str, int]
) -> collections.abc.Mapping[str, int]:
    return {**map1, **map2}


def invalid_types(attr1: int, attr2: UnknownClass, attr3: str) -> None:  # noqa: F821
    pass
