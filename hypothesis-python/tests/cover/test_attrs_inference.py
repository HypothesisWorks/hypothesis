# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
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

from __future__ import absolute_import, division, print_function

import attr
import pytest

import hypothesis.strategies as st
from hypothesis import given, infer
from hypothesis.errors import ResolutionFailed

try:
    import typing
except ImportError:
    typing = None


@attr.s
class Inferrables(object):
    type_ = attr.ib(type=int)
    type_converter = attr.ib(converter=bool)
    validator_type = attr.ib(validator=attr.validators.instance_of(str))
    validator_type_tuple = attr.ib(validator=attr.validators.instance_of((str, int)))
    validator_type_multiple = attr.ib(
        validator=[
            attr.validators.instance_of(str),
            attr.validators.instance_of((str, int, bool)),
        ]
    )
    validator_type_has_overlap = attr.ib(
        validator=[
            attr.validators.instance_of(str),
            attr.validators.instance_of((str, list)),
            attr.validators.instance_of(object),
        ]
    )
    validator_optional = attr.ib(
        validator=attr.validators.optional(lambda inst, atrib, val: float(val))
    )
    validator_in = attr.ib(validator=attr.validators.in_([1, 2, 3]))
    validator_in_multiple = attr.ib(
        validator=[attr.validators.in_(list(range(100))), attr.validators.in_([1, -1])]
    )
    validator_in_multiple_strings = attr.ib(
        validator=[attr.validators.in_("abcd"), attr.validators.in_(["ab", "cd"])]
    )

    if typing is not None:
        typing_list = attr.ib(type=typing.List[int])
        typing_list_of_list = attr.ib(type=typing.List[typing.List[int]])
        typing_dict = attr.ib(type=typing.Dict[str, int])
        typing_union = attr.ib(type=typing.Optional[bool])
        typing_union = attr.ib(type=typing.Union[str, int])

    has_default = attr.ib(default=0)
    has_default_factory = attr.ib(default=attr.Factory(list))
    has_default_factory_takes_self = attr.ib(  # uninferrable but has default
        default=attr.Factory(lambda _: list(), takes_self=True)
    )


@attr.s
class Required(object):
    a = attr.ib()


@attr.s
class UnhelpfulConverter(object):
    a = attr.ib(converter=lambda x: x)


@given(st.builds(Inferrables, has_default=infer, has_default_factory=infer))
def test_attrs_inference_builds(c):
    pass


@given(st.from_type(Inferrables))
def test_attrs_inference_from_type(c):
    pass


@pytest.mark.parametrize("c", [Required, UnhelpfulConverter])
def test_cannot_infer(c):
    with pytest.raises(ResolutionFailed):
        st.builds(c).example()


def test_cannot_infer_takes_self():
    with pytest.raises(ResolutionFailed):
        st.builds(Inferrables, has_default_factory_takes_self=infer).example()
