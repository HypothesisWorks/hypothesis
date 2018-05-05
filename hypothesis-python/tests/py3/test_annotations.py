# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import pytest

import hypothesis.strategies as st
from hypothesis import given
from hypothesis.errors import InvalidArgument
from hypothesis._internal.compat import getfullargspec
from hypothesis._internal.reflection import define_function_signature, \
    convert_positional_arguments, get_pretty_function_description


@given(st.integers())
def test_has_an_annotation(i: int):
    pass


def universal_acceptor(*args, **kwargs):
    return args, kwargs


def has_annotation(a: int, *b, c=2) -> None:
    pass


@pytest.mark.parametrize('f', [
    has_annotation,
    lambda *, a: a,
    lambda *, a=1: a,
])
def test_copying_preserves_argspec(f):
    af = getfullargspec(f)
    t = define_function_signature('foo', 'docstring', af)(universal_acceptor)
    at = getfullargspec(t)
    assert af.args == at.args[:len(af.args)]
    assert af.varargs == at.varargs
    assert af.varkw == at.varkw
    assert len(af.defaults or ()) == len(at.defaults or ())
    assert af.kwonlyargs == at.kwonlyargs
    assert af.kwonlydefaults == at.kwonlydefaults
    assert af.annotations == at.annotations


@pytest.mark.parametrize('lam,source', [
    ((lambda *z, a: a),
     'lambda *z, a: a'),
    ((lambda *z, a=1: a),
     'lambda *z, a=1: a'),
    ((lambda *, a: a),
     'lambda *, a: a'),
    ((lambda *, a=1: a),
     'lambda *, a=1: a'),
])
def test_py3only_lambda_formatting(lam, source):
    # Testing kwonly lambdas, with and without varargs and default values
    assert get_pretty_function_description(lam) == source


def test_given_notices_missing_kwonly_args():
    with pytest.raises(InvalidArgument):
        @given(a=st.none())
        def reqs_kwonly(*, a, b):
            pass


def test_converter_handles_kwonly_args():
    def f(*, a, b=2):
        pass

    out = convert_positional_arguments(f, (), dict(a=1))
    assert out == ((), dict(a=1, b=2))


def test_converter_notices_missing_kwonly_args():
    def f(*, a, b=2):
        pass

    with pytest.raises(TypeError):
        assert convert_positional_arguments(f, (), dict())


def pointless_composite(draw: None, strat: bool, nothing: list) -> int:
    return 3


def return_annot() -> int:
    return 4  # per RFC 1149.5 / xckd 221


def first_annot(draw: None):
    pass


def test_composite_edits_annotations():
    spec_comp = getfullargspec(st.composite(pointless_composite))
    assert spec_comp.annotations['return'] == int
    assert 'nothing' in spec_comp.annotations
    assert 'draw' not in spec_comp.annotations


@pytest.mark.parametrize('nargs', [1, 2, 3])
def test_given_edits_annotations(nargs):
    spec_given = getfullargspec(
        given(*(nargs * [st.none()]))(pointless_composite))
    assert spec_given.annotations.pop('return') is None
    assert len(spec_given.annotations) == 3 - nargs
