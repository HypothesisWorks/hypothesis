# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import sys
import typing

import attr
import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import ResolutionFailed

from tests.common.debug import check_can_generate_examples


@attr.s
class Inferrables:
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

    typing_list = attr.ib(type=list[int])
    typing_list_of_list = attr.ib(type=list[list[int]])
    typing_dict = attr.ib(type=dict[str, int])
    typing_optional = attr.ib(type=typing.Optional[bool])
    typing_union = attr.ib(type=typing.Union[str, int])

    has_default = attr.ib(default=0)
    has_default_factory = attr.ib(default=attr.Factory(list))
    has_default_factory_takes_self = attr.ib(  # uninferrable but has default
        default=attr.Factory(lambda _: [], takes_self=True)
    )


@attr.s
class Required:
    a = attr.ib()


@attr.s
class UnhelpfulConverter:
    a = attr.ib(converter=lambda x: x)


@given(st.builds(Inferrables, has_default=..., has_default_factory=...))
def test_attrs_inference_builds(c):
    pass


@given(st.from_type(Inferrables))
def test_attrs_inference_from_type(c):
    pass


@pytest.mark.parametrize("c", [Required, UnhelpfulConverter])
def test_cannot_infer(c):
    with pytest.raises(ResolutionFailed):
        check_can_generate_examples(st.builds(c))


def test_cannot_infer_takes_self():
    with pytest.raises(ResolutionFailed):
        check_can_generate_examples(
            st.builds(Inferrables, has_default_factory_takes_self=...)
        )


@attr.s
class HasPrivateAttribute:
    _x: int = attr.ib()


skip_on_314 = pytest.mark.skipif(sys.version_info[:2] >= (3, 14), reason="FIXME-py314")


@pytest.mark.parametrize("s", [st.just(42), pytest.param(..., marks=skip_on_314)])
def test_private_attribute(s):
    check_can_generate_examples(st.builds(HasPrivateAttribute, x=s))


@skip_on_314
def test_private_attribute_underscore_fails():
    with pytest.raises(TypeError, match="unexpected keyword argument '_x'"):
        check_can_generate_examples(st.builds(HasPrivateAttribute, _x=st.just(42)))


@skip_on_314
def test_private_attribute_underscore_infer_fails():
    # this has a slightly different failure case, because it goes through
    # attrs-specific resolution logic.
    with pytest.raises(
        TypeError, match="Unexpected keyword argument _x for attrs class"
    ):
        check_can_generate_examples(st.builds(HasPrivateAttribute, _x=...))


@attr.s
class HasAliasedAttribute:
    x: int = attr.ib(alias="crazyname")


@pytest.mark.parametrize("s", [st.just(42), pytest.param(..., marks=skip_on_314)])
def test_aliased_attribute(s):
    check_can_generate_examples(st.builds(HasAliasedAttribute, crazyname=s))
