# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import warnings

import attr

from hypothesis import given, strategies as st
from hypothesis.errors import SmallSearchSpaceWarning

from tests.common.debug import check_can_generate_examples
from hypothesis.strategies._internal.utils import to_jsonable


def a_converter(x) -> int:
    return int(x)


@attr.s
class Inferrables:
    annot_converter = attr.ib(converter=a_converter)


@given(st.builds(Inferrables))
def test_attrs_inference_builds(c):
    pass


def test_attrs_inference_from_type():
    s = st.from_type(Inferrables)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SmallSearchSpaceWarning)
        check_can_generate_examples(s)


@attr.s
class AttrsClass:
    n = attr.ib()


def test_jsonable_attrs():
    obj = AttrsClass(n=10)
    assert to_jsonable(obj, avoid_realization=False) == {"n": 10}
