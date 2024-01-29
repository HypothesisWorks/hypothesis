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
from inspect import Parameter as P, signature

import attr
import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import SmallSearchSpaceWarning
from hypothesis.internal.reflection import (
    convert_positional_arguments,
    define_function_signature,
    get_pretty_function_description,
)

from tests.common.debug import check_can_generate_examples


@given(st.integers())
def test_has_an_annotation(i: int):
    pass


def universal_acceptor(*args, **kwargs):
    return args, kwargs


def has_annotation(a: int, *b, c=2) -> None:
    pass


@pytest.mark.parametrize("f", [has_annotation, lambda *, a: a, lambda *, a=1: a])
def test_copying_preserves_signature(f):
    af = signature(f)
    t = define_function_signature("foo", "docstring", af)(universal_acceptor)
    at = signature(t)
    assert af.parameters == at.parameters


@pytest.mark.parametrize(
    "lam,source",
    [
        ((lambda *z, a: a), "lambda *z, a: a"),
        ((lambda *z, a=1: a), "lambda *z, a=1: a"),
        ((lambda *, a: a), "lambda *, a: a"),
        ((lambda *, a=1: a), "lambda *, a=1: a"),
        ((lambda **kw: kw), "lambda **kw: kw"),
    ],
)
def test_kwonly_lambda_formatting(lam, source):
    # Testing kwonly lambdas, with and without varargs and default values
    assert get_pretty_function_description(lam) == source


def test_given_notices_missing_kwonly_args():
    @given(a=st.none())
    def reqs_kwonly(*, a, b):
        pass

    with pytest.raises(TypeError):
        reqs_kwonly()
    reqs_kwonly(b=None)


def test_converter_handles_kwonly_args():
    def f(*, a, b=2):
        pass

    out = convert_positional_arguments(f, (), {"a": 1})
    assert out == ((), {"a": 1})


def test_converter_notices_missing_kwonly_args():
    def f(*, a, b=2):
        pass

    with pytest.raises(TypeError):
        assert convert_positional_arguments(f, (), {})


def to_wrap_with_composite(draw: None, strat: float, nothing: list) -> int:
    return draw(st.none())


def return_annot() -> int:
    return 4  # per RFC 1149.5 / xckd 221


def first_annot(draw: None):
    pass


def test_composite_edits_annotations():
    sig_comp = signature(st.composite(to_wrap_with_composite))
    assert sig_comp.return_annotation == st.SearchStrategy[int]
    assert sig_comp.parameters["nothing"].annotation is not P.empty
    assert "draw" not in sig_comp.parameters


@pytest.mark.parametrize("nargs", [1, 2, 3])
def test_given_edits_annotations(nargs):
    sig_given = signature(given(*(nargs * [st.none()]))(to_wrap_with_composite))
    assert sig_given.return_annotation is None
    assert len(sig_given.parameters) == 3 - nargs
    assert all(p.annotation is not P.empty for p in sig_given.parameters.values())


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
