# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import ast

import pytest

from hypothesis.vendor import pretty


def _try_inline_lambda(func_name, args=(), kwargs=None):
    """Helper: run _try_inline_lambda and return the printer output, or None."""
    if kwargs is None:
        kwargs = {}
    p = pretty.RepresentationPrinter()
    if not pretty._try_inline_lambda(func_name, args, kwargs, p):
        return None
    return p.getvalue()


class BadRepr:
    def __repr__(self):
        return "not valid(python syntax"


@pytest.mark.parametrize(
    "func_name, args, kwargs, expected",
    [
        pytest.param("lambda: 42", (), {}, "42", id="no_args"),
        pytest.param("lambda x: x + 1", (0,), {}, "0 + 1", id="single_positional"),
        pytest.param("lambda x: x + 1", (), {"x": 0}, "0 + 1", id="single_kwarg"),
        pytest.param(
            "lambda a, b: (b, a)",
            ("hello", "world"),
            {},
            "('world', 'hello')",
            id="multi_positional",
        ),
        pytest.param(
            "lambda a, b: a + b", (), {"a": 1, "b": 2}, "1 + 2", id="multi_kwargs"
        ),
        pytest.param(
            "lambda a, b: a + b",
            (1,),
            {"b": 2},
            "1 + 2",
            id="mixed_positional_and_kwargs",
        ),
        pytest.param("lambda x: 42", (99,), {}, "42", id="unused_param"),
        pytest.param(
            "lambda a, b, c: 42", (1, 2, 3), {}, "42", id="unused_params_multi"
        ),
        pytest.param(
            "lambda s: s.upper()", ("hi",), {}, "'hi'.upper()", id="method_call"
        ),
        pytest.param("lambda b: f(b).g()", (0,), {}, "f(0).g()", id="nested_call"),
        pytest.param(
            "lambda a, b=10: a + 1",
            (),
            {"a": 5},
            "5 + 1",
            id="default_not_passed",
        ),
        pytest.param(
            "lambda a, b=10: a + b",
            (),
            {"a": 5, "b": 20},
            "5 + 20",
            id="default_passed",
        ),
        pytest.param("lambda a, b=1, c=2: a", (99,), {}, "99", id="multiple_defaults"),
    ],
)
def test_inline_success(func_name, args, kwargs, expected):
    assert _try_inline_lambda(func_name, args, kwargs) == expected


@pytest.mark.parametrize(
    "func_name, args, kwargs",
    [
        pytest.param("not a lambda at all!!!", (), {}, id="syntax_error"),
        pytest.param("foo", (), {}, id="not_a_lambda"),
        pytest.param("lambda *args: args", ((1, 2),), {}, id="vararg"),
        pytest.param("lambda **kw: kw", (), {"a": 1}, id="kwarg_star"),
        pytest.param("lambda *, x: x", (), {"x": 1}, id="kwonly_args"),
        pytest.param("lambda x: (x, x)", (1,), {}, id="param_used_twice"),
        pytest.param("lambda x: x + x", (1,), {}, id="param_used_twice_different"),
        pytest.param("lambda a, b: a + b", (1,), {}, id="too_few_args_no_default"),
        pytest.param("lambda x: x", (), {"y": 1}, id="wrong_kwarg_name"),
        pytest.param("lambda: 42", (1, 2), {}, id="more_args_than_params"),
        pytest.param("lambda x: x", (BadRepr(),), {}, id="invalid_repr"),
    ],
)
def test_inline_bail_out(func_name, args, kwargs):
    assert _try_inline_lambda(func_name, args, kwargs) is None


@pytest.mark.parametrize(
    "func_name, args, kwargs, expected",
    [
        pytest.param("lambda: 0", (), {}, "0", id="no_arg_lambda"),
        pytest.param("lambda x: x", (1,), {}, "1", id="identity"),
        pytest.param("lambda a, b: a - b", (10, 3), {}, "10 - 3", id="subtraction"),
        pytest.param(
            "lambda x: (x, x)", (1,), {}, "(lambda x: (x, x))(1)", id="multi_use"
        ),
        pytest.param("lambda x: [x]", (1,), {}, "[1]", id="list_wrap"),
        pytest.param(
            "lambda s: s.strip()", ("  hi  ",), {}, "'  hi  '.strip()", id="strip"
        ),
        pytest.param("lambda: None", (), {}, "None", id="none"),
        pytest.param("lambda x: f(x)", (42,), {}, "f(42)", id="inlines_single_use"),
        pytest.param("lambda: 42", (), {}, "42", id="inlines_no_arg"),
        pytest.param(
            "lambda *args: args",
            ((1, 2),),
            {},
            "(lambda *args: args)((1, 2))",
            id="wraps_vararg",
        ),
        pytest.param("foo", (1, 2), {}, "foo(1, 2)", id="non_lambda_unchanged"),
    ],
)
def test_repr_call_parametrized(func_name, args, kwargs, expected):
    p = pretty.RepresentationPrinter()
    p.repr_call(func_name, args, kwargs)
    assert p.getvalue() == expected


def test_unparse_failure_returns_none(monkeypatch):
    real_unparse = ast.unparse
    called = False

    def bad_unparse(node):
        nonlocal called
        if not called:
            called = True
            raise ValueError("boom")
        return real_unparse(node)

    monkeypatch.setattr(ast, "unparse", bad_unparse)
    assert _try_inline_lambda("lambda x: x", args=(1,)) is None


def test_repr_call_skips_inlining_when_comments_present():
    p = pretty.RepresentationPrinter()
    # Simulate explain-mode comments on slice (0, 5)
    p.slice_comments[(0, 5)] = "or any other generated value"
    p.repr_call(
        "lambda x: f(x)",
        args=(42,),
        kwargs={},
        arg_slices={"arg[0]": (0, 5)},
    )
    result = p.getvalue()
    # Should NOT inline — must keep call style for the comment
    assert result.startswith("(lambda x: f(x))")
    assert "# or any other generated value" in result


def test_repr_call_inlines_when_arg_slices_but_no_comments():
    p = pretty.RepresentationPrinter()
    # arg_slices present but no matching slice_comments
    p.repr_call(
        "lambda x: f(x)",
        args=(42,),
        kwargs={},
        arg_slices={"arg[0]": (0, 5)},
    )
    assert p.getvalue() == "f(42)"
