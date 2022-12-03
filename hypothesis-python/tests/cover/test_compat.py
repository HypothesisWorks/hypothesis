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
from dataclasses import dataclass
from inspect import Parameter, Signature, signature
from typing import ForwardRef

import pytest

from hypothesis.internal.compat import ceil, floor, get_type_hints

floor_ceil_values = [
    -10.7,
    -10.3,
    -0.5,
    -0.0,
    0,
    0.5,
    10.3,
    10.7,
]


@pytest.mark.parametrize("value", floor_ceil_values)
def test_our_floor_agrees_with_math_floor(value):
    assert floor(value) == math.floor(value)


@pytest.mark.parametrize("value", floor_ceil_values)
def test_our_ceil_agrees_with_math_ceil(value):
    assert ceil(value) == math.ceil(value)


class WeirdSig:
    __signature__ = Signature(
        parameters=[Parameter(name="args", kind=Parameter.VAR_POSITIONAL)]
    )


def test_no_type_hints():
    assert get_type_hints(WeirdSig) == {}


@dataclass
class Foo:
    x: "Foo" = None  # type: ignore


Foo.__signature__ = signature(Foo).replace(  # type: ignore
    parameters=[
        Parameter(
            "x",
            Parameter.POSITIONAL_OR_KEYWORD,
            annotation=ForwardRef("Foo"),
        )
    ]
)


def test_resolve_fwd_refs():
    # See: https://github.com/HypothesisWorks/hypothesis/issues/3519
    assert get_type_hints(Foo)["x"] is Optional[Foo]
