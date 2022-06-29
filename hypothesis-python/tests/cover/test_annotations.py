# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from inspect import getfullargspec

import attr
import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.internal.reflection import (
    convert_positional_arguments,
    define_function_signature,
    get_pretty_function_description,
)


@given(st.integers())
def test_has_an_annotation(i: int):
    pass


def universal_acceptor(*args, **kwargs):
    return args, kwargs


def has_annotation(a: int, *b, c=2) -> None:
    pass


@pytest.mark.parametrize("f", [has_annotation, lambda *, a: a, lambda *, a=1: a])
def test_copying_preserves_argspec(f):
    af = getfullargspec(f)
    t = define_function_signature("foo", "docstring", af)(universal_acceptor)
    at = getfullargspec(t)
    assert af.args == at.args[: len(af.args)]
    assert af.varargs == at.varargs
    assert af.varkw == at.varkw
    assert len(af.defaults or ()) == len(at.defaults or ())
    assert af.kwonlyargs == at.kwonlyargs
    assert af.kwonlydefaults == at.kwonlydefaults
    assert af.annotations == at.annotations


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

    with pytest.raises(InvalidArgument):
        reqs_kwonly()


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


def pointless_composite(draw: None, strat: bool, nothing: list) -> int:
    return 3


def return_annot() -> int:
    return 4  # per RFC 1149.5 / xckd 221


def first_annot(draw: None):
    pass


def test_composite_edits_annotations():
    spec_comp = getfullargspec(st.composite(pointless_composite))
    assert spec_comp.annotations["return"] == st.SearchStrategy[int]
    assert "nothing" in spec_comp.annotations
    assert "draw" not in spec_comp.annotations


@pytest.mark.parametrize("nargs", [1, 2, 3])
def test_given_edits_annotations(nargs):
    spec_given = getfullargspec(given(*(nargs * [st.none()]))(pointless_composite))
    assert spec_given.annotations.pop("return") is None
    assert len(spec_given.annotations) == 3 - nargs


def a_converter(x) -> int:
    return int(x)


@attr.s
class Inferrables:
    annot_converter = attr.ib(converter=a_converter)


@given(st.builds(Inferrables))
def test_attrs_inference_builds(c):
    pass


@given(st.from_type(Inferrables))
def test_attrs_inference_from_type(c):
    pass
