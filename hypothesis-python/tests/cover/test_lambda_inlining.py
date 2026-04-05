# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from hypothesis.vendor import pretty


def _inline(func_name, args=(), kwargs=None):
    """Helper: run _try_inline_lambda and return the printer output, or None."""
    if kwargs is None:
        kwargs = {}
    p = pretty.RepresentationPrinter()
    result = pretty._try_inline_lambda(func_name, args, kwargs, p)
    if result is None:
        return None
    return p.getvalue()


def _repr_call(func_name, args=(), kwargs=None):
    """Helper: run repr_call and return the full output string."""
    if kwargs is None:
        kwargs = {}
    p = pretty.RepresentationPrinter()
    p.repr_call(func_name, args, kwargs)
    return p.getvalue()


# --- Success cases ---


def test_no_arg_lambda():
    assert _inline("lambda: 42") == "42"


def test_single_positional_arg():
    assert _inline("lambda x: x + 1", args=(0,)) == "0 + 1"


def test_single_kwarg():
    assert _inline("lambda x: x + 1", kwargs={"x": 0}) == "0 + 1"


def test_multi_positional_args():
    assert (
        _inline("lambda a, b: (b, a)", args=("hello", "world")) == "('world', 'hello')"
    )


def test_multi_kwargs():
    assert _inline("lambda a, b: a + b", kwargs={"a": 1, "b": 2}) == "1 + 2"


def test_mixed_positional_and_kwargs():
    assert _inline("lambda a, b: a + b", args=(1,), kwargs={"b": 2}) == "1 + 2"


def test_unused_param():
    assert _inline("lambda x: 42", args=(99,)) == "42"


def test_unused_params_multi():
    assert _inline("lambda a, b, c: 42", args=(1, 2, 3)) == "42"


def test_method_call_on_arg():
    assert _inline("lambda s: s.upper()", args=("hi",)) == "'hi'.upper()"


def test_nested_call():
    result = _inline("lambda b: f(b).g()", args=(0,))
    assert result == "f(0).g()"


def test_param_with_default_not_passed():
    assert _inline("lambda a, b=10: a + 1", kwargs={"a": 5}) == "5 + 1"


def test_param_with_default_passed():
    assert _inline("lambda a, b=10: a + b", kwargs={"a": 5, "b": 20}) == "5 + 20"


def test_multiple_defaults():
    assert _inline("lambda a, b=1, c=2: a", args=(99,)) == "99"


# --- Bail-out cases ---


def test_syntax_error_returns_none():
    assert _inline("not a lambda at all!!!") is None


def test_not_a_lambda_returns_none():
    assert _inline("foo") is None


def test_vararg_returns_none():
    assert _inline("lambda *args: args", args=((1, 2),)) is None


def test_kwarg_star_returns_none():
    assert _inline("lambda **kw: kw", kwargs={"a": 1}) is None


def test_kwonly_args_returns_none():
    assert _inline("lambda *, x: x", kwargs={"x": 1}) is None


def test_param_used_twice_returns_none():
    assert _inline("lambda x: (x, x)", args=(1,)) is None


def test_param_used_twice_in_different_contexts():
    assert _inline("lambda x: x + x", args=(1,)) is None


def test_too_few_args_no_default():
    assert _inline("lambda a, b: a + b", args=(1,)) is None


def test_wrong_kwarg_name():
    assert _inline("lambda x: x", kwargs={"y": 1}) is None


def test_more_args_than_params():
    assert _inline("lambda: 42", args=(1, 2)) is None


def test_invalid_repr_returns_none():
    class BadRepr:
        def __repr__(self):
            return "not valid(python syntax"

    assert _inline("lambda x: x", args=(BadRepr(),)) is None


# --- Integration through repr_call ---


def test_repr_call_inlines_single_use_lambda():
    assert _repr_call("lambda x: f(x)", args=(42,)) == "f(42)"


def test_repr_call_inlines_no_arg_lambda():
    assert _repr_call("lambda: 42") == "42"


def test_repr_call_wraps_when_multi_use():
    assert _repr_call("lambda x: (x, x)", args=(1,)) == "(lambda x: (x, x))(1)"


def test_repr_call_wraps_when_vararg():
    assert _repr_call("lambda *args: args", args=((1, 2),)) == (
        "(lambda *args: args)((1, 2))"
    )


def test_unparse_failure_returns_none(monkeypatch):
    import ast as ast_mod

    real_unparse = ast_mod.unparse
    called = False

    def bad_unparse(node):
        nonlocal called
        if not called:
            called = True
            raise ValueError("boom")
        return real_unparse(node)

    monkeypatch.setattr(ast_mod, "unparse", bad_unparse)
    assert _inline("lambda x: x", args=(1,)) is None


def test_repr_call_non_lambda_unchanged():
    assert _repr_call("foo", args=(1, 2)) == "foo(1, 2)"


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


@pytest.mark.parametrize(
    "func_name, args, kwargs, expected",
    [
        ("lambda: 0", (), {}, "0"),
        ("lambda x: x", (1,), {}, "1"),
        ("lambda a, b: a - b", (10, 3), {}, "10 - 3"),
        ("lambda x: (x, x)", (1,), {}, "(lambda x: (x, x))(1)"),
        ("lambda x: [x]", (1,), {}, "[1]"),
        ("lambda s: s.strip()", ("  hi  ",), {}, "'  hi  '.strip()"),
        ("lambda: None", (), {}, "None"),
    ],
)
def test_repr_call_parametrized(func_name, args, kwargs, expected):
    assert _repr_call(func_name, args, kwargs) == expected
