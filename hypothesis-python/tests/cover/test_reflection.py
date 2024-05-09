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
from copy import deepcopy
from datetime import time
from functools import partial, wraps
from inspect import Parameter, Signature, signature
from textwrap import dedent
from unittest.mock import MagicMock, Mock, NonCallableMagicMock, NonCallableMock

import pytest
from pytest import raises

from hypothesis import given, strategies as st
from hypothesis.errors import HypothesisWarning
from hypothesis.internal import reflection
from hypothesis.internal.reflection import (
    convert_keyword_arguments,
    convert_positional_arguments,
    define_function_signature,
    function_digest,
    get_pretty_function_description,
    get_signature,
    is_first_param_referenced_in_function,
    is_mock,
    proxies,
    repr_call,
    required_args,
    source_exec_as_module,
)
from hypothesis.strategies._internal.lazy import LazyStrategy


def do_conversion_test(f, args, kwargs):
    result = f(*args, **kwargs)

    cargs, ckwargs = convert_keyword_arguments(f, args, kwargs)
    assert result == f(*cargs, **ckwargs)

    cargs2, ckwargs2 = convert_positional_arguments(f, args, kwargs)
    assert result == f(*cargs2, **ckwargs2)


def test_simple_conversion():
    def foo(a, b, c):
        return (a, b, c)

    assert convert_keyword_arguments(foo, (1, 2, 3), {}) == ((1, 2, 3), {})
    assert convert_keyword_arguments(foo, (), {"a": 3, "b": 2, "c": 1}) == (
        (3, 2, 1),
        {},
    )

    do_conversion_test(foo, (1, 0), {"c": 2})
    do_conversion_test(foo, (1,), {"c": 2, "b": "foo"})


def test_leaves_unknown_kwargs_in_dict():
    def bar(x, **kwargs):
        pass

    assert convert_keyword_arguments(bar, (1,), {"foo": "hi"}) == ((1,), {"foo": "hi"})
    assert convert_keyword_arguments(bar, (), {"x": 1, "foo": "hi"}) == (
        (1,),
        {"foo": "hi"},
    )
    do_conversion_test(bar, (1,), {})
    do_conversion_test(bar, (), {"x": 1, "y": 1})


def test_errors_on_bad_kwargs():
    def bar():
        pass

    with raises(TypeError):
        convert_keyword_arguments(bar, (), {"foo": 1})


def test_passes_varargs_correctly():
    def foo(*args):
        pass

    assert convert_keyword_arguments(foo, (1, 2, 3), {}) == ((1, 2, 3), {})

    do_conversion_test(foo, (1, 2, 3), {})


def test_errors_if_keyword_precedes_positional():
    def foo(x, y):
        pass

    with raises(TypeError):
        convert_keyword_arguments(foo, (1,), {"x": 2})


def test_errors_if_not_enough_args():
    def foo(a, b, c, d=1):
        pass

    with raises(TypeError):
        convert_keyword_arguments(foo, (1, 2), {"d": 4})


def test_errors_on_extra_kwargs():
    def foo(a):
        pass

    with raises(TypeError, match="keyword"):
        convert_keyword_arguments(foo, (1,), {"b": 1})

    with raises(TypeError, match="keyword"):
        convert_keyword_arguments(foo, (1,), {"b": 1, "c": 2})


def test_positional_errors_if_too_many_args():
    def foo(a):
        pass

    with raises(TypeError, match="too many positional arguments"):
        convert_positional_arguments(foo, (1, 2), {})


def test_positional_errors_if_too_few_args():
    def foo(a, b, c):
        pass

    with raises(TypeError):
        convert_positional_arguments(foo, (1, 2), {})


def test_positional_does_not_error_if_extra_args_are_kwargs():
    def foo(a, b, c):
        pass

    convert_positional_arguments(foo, (1, 2), {"c": 3})


def test_positional_errors_if_given_bad_kwargs():
    def foo(a):
        pass

    with raises(TypeError, match="missing a required argument: 'a'"):
        convert_positional_arguments(foo, (), {"b": 1})


def test_positional_errors_if_given_duplicate_kwargs():
    def foo(a):
        pass

    with raises(TypeError, match="multiple values"):
        convert_positional_arguments(foo, (2,), {"a": 1})


def test_names_of_functions_are_pretty():
    assert (
        get_pretty_function_description(test_names_of_functions_are_pretty)
        == "test_names_of_functions_are_pretty"
    )


class Foo:
    @classmethod
    def bar(cls):
        pass

    def baz(cls):
        pass

    def __repr__(self):
        return "SoNotFoo()"


def test_class_names_are_not_included_in_class_method_prettiness():
    assert get_pretty_function_description(Foo.bar) == "bar"


def test_repr_is_included_in_bound_method_prettiness():
    assert get_pretty_function_description(Foo().baz) == "SoNotFoo().baz"


def test_class_is_not_included_in_unbound_method():
    assert get_pretty_function_description(Foo.baz) == "baz"


def test_does_not_error_on_confused_sources():
    def ed(f, *args):
        return f

    x = ed(
        lambda x, y: (x * y).conjugate() == x.conjugate() * y.conjugate(),
        complex,
        complex,
    )

    get_pretty_function_description(x)


def test_digests_are_reasonably_unique():
    assert function_digest(test_simple_conversion) != function_digest(
        test_does_not_error_on_confused_sources
    )


def test_digest_returns_the_same_value_for_two_calls():
    assert function_digest(test_simple_conversion) == function_digest(
        test_simple_conversion
    )


def test_can_digest_a_built_in_function():
    import math

    assert function_digest(math.isnan) != function_digest(range)


def test_can_digest_a_unicode_lambda():
    function_digest(lambda x: "☃" in str(x))


def test_can_digest_a_function_with_no_name():
    def foo(x, y):
        pass

    function_digest(partial(foo, 1))


def test_arg_string_is_in_order():
    def foo(c, a, b, f, a1):
        pass

    assert repr_call(foo, (1, 2, 3, 4, 5), {}) == "foo(c=1, a=2, b=3, f=4, a1=5)"
    assert (
        repr_call(foo, (1, 2), {"b": 3, "f": 4, "a1": 5})
        == "foo(c=1, a=2, b=3, f=4, a1=5)"
    )


def test_varkwargs_are_sorted_and_after_real_kwargs():
    def foo(d, e, f, **kwargs):
        pass

    assert (
        repr_call(foo, (), {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6})
        == "foo(d=4, e=5, f=6, a=1, b=2, c=3)"
    )


def test_varargs_come_without_equals():
    def foo(a, *args):
        pass

    assert repr_call(foo, (1, 2, 3, 4), {}) == "foo(2, 3, 4, a=1)"


def test_can_mix_varargs_and_varkwargs():
    def foo(*args, **kwargs):
        pass

    assert repr_call(foo, (1, 2, 3), {"c": 7}) == "foo(1, 2, 3, c=7)"


def test_arg_string_does_not_include_unprovided_defaults():
    def foo(a, b, c=9, d=10):
        pass

    assert repr_call(foo, (1,), {"b": 1, "d": 11}) == "foo(a=1, b=1, d=11)"


def universal_acceptor(*args, **kwargs):
    return args, kwargs


def has_one_arg(hello):
    pass


def has_two_args(hello, world):
    pass


def has_a_default(x, y, z=1):
    pass


def has_varargs(*args):
    pass


def has_kwargs(**kwargs):
    pass


@pytest.mark.parametrize("f", [has_one_arg, has_two_args, has_varargs, has_kwargs])
def test_copying_preserves_signature(f):
    af = get_signature(f)
    t = define_function_signature("foo", "docstring", af)(universal_acceptor)
    at = get_signature(t)
    assert af == at


def test_name_does_not_clash_with_function_names():
    def f():
        pass

    @define_function_signature("f", "A docstring for f", signature(f))
    def g():
        pass

    g()


def test_copying_sets_name():
    f = define_function_signature(
        "hello_world", "A docstring for hello_world", signature(has_two_args)
    )(universal_acceptor)
    assert f.__name__ == "hello_world"


def test_copying_sets_docstring():
    f = define_function_signature(
        "foo", "A docstring for foo", signature(has_two_args)
    )(universal_acceptor)
    assert f.__doc__ == "A docstring for foo"


def test_uses_defaults():
    f = define_function_signature(
        "foo", "A docstring for foo", signature(has_a_default)
    )(universal_acceptor)
    assert f(3, 2) == ((3, 2, 1), {})


def test_uses_varargs():
    f = define_function_signature("foo", "A docstring for foo", signature(has_varargs))(
        universal_acceptor
    )
    assert f(1, 2) == ((1, 2), {})


DEFINE_FOO_FUNCTION = """
def foo(x):
    return x
"""


def test_exec_as_module_execs():
    m = source_exec_as_module(DEFINE_FOO_FUNCTION)
    assert m.foo(1) == 1


def test_exec_as_module_caches():
    assert source_exec_as_module(DEFINE_FOO_FUNCTION) is source_exec_as_module(
        DEFINE_FOO_FUNCTION
    )


def test_exec_leaves_sys_path_unchanged():
    old_path = deepcopy(sys.path)
    source_exec_as_module("hello_world = 42")
    assert sys.path == old_path


def test_define_function_signature_works_with_conflicts():
    def accepts_everything(*args, **kwargs):
        pass

    define_function_signature(
        "hello",
        "A docstring for hello",
        Signature(parameters=[Parameter("f", Parameter.POSITIONAL_OR_KEYWORD)]),
    )(accepts_everything)(1)

    define_function_signature(
        "hello",
        "A docstring for hello",
        Signature(parameters=[Parameter("f", Parameter.VAR_POSITIONAL)]),
    )(accepts_everything)(1)

    define_function_signature(
        "hello",
        "A docstring for hello",
        Signature(parameters=[Parameter("f", Parameter.VAR_KEYWORD)]),
    )(accepts_everything)()

    define_function_signature(
        "hello",
        "A docstring for hello",
        Signature(
            parameters=[
                Parameter("f", Parameter.POSITIONAL_OR_KEYWORD),
                Parameter("f_3", Parameter.POSITIONAL_OR_KEYWORD),
                Parameter("f_1", Parameter.VAR_POSITIONAL),
                Parameter("f_2", Parameter.VAR_KEYWORD),
            ]
        ),
    )(accepts_everything)(1, 2)


def test_define_function_signature_validates_function_name():
    define_function_signature("hello_world", None, Signature())
    with raises(ValueError):
        define_function_signature("hello world", None, Signature())


class Container:
    def funcy(self):
        pass


def test_can_proxy_functions_with_mixed_args_and_varargs():
    def foo(a, *args):
        return (a, args)

    @proxies(foo)
    def bar(*args, **kwargs):
        return foo(*args, **kwargs)

    assert bar(1, 2) == (1, (2,))


def test_can_delegate_to_a_function_with_no_positional_args():
    def foo(a, b):
        return (a, b)

    @proxies(foo)
    def bar(**kwargs):
        return foo(**kwargs)

    assert bar(2, 1) == (2, 1)


@pytest.mark.parametrize(
    "func,args,expected",
    [
        (lambda: None, (), None),
        (lambda a: a**2, (2,), 4),
        (lambda *a: a, [1, 2, 3], (1, 2, 3)),
    ],
)
def test_can_proxy_lambdas(func, args, expected):
    @proxies(func)
    def wrapped(*args, **kwargs):
        return func(*args, **kwargs)

    assert wrapped.__name__ == "<lambda>"
    assert wrapped(*args) == expected


class Snowman:
    def __repr__(self):
        return "☃"


class BittySnowman:
    def __repr__(self):
        return "☃"


def test_can_handle_unicode_repr():
    def foo(x):
        pass

    assert repr_call(foo, [Snowman()], {}) == "foo(x=☃)"
    assert repr_call(foo, [], {"x": Snowman()}) == "foo(x=☃)"


class NoRepr:
    pass


def test_can_handle_repr_on_type():
    def foo(x):
        pass

    assert repr_call(foo, [Snowman], {}) == "foo(x=Snowman)"
    assert repr_call(foo, [NoRepr], {}) == "foo(x=NoRepr)"


def test_can_handle_repr_of_none():
    def foo(x):
        pass

    assert repr_call(foo, [None], {}) == "foo(x=None)"
    assert repr_call(foo, [], {"x": None}) == "foo(x=None)"


def test_kwargs_appear_in_arg_string():
    def varargs(*args, **kwargs):
        pass

    assert "x=1" in repr_call(varargs, (), {"x": 1})


def test_is_mock_with_negative_cases():
    assert not is_mock(None)
    assert not is_mock(1234)
    assert not is_mock(is_mock)
    assert not is_mock(BittySnowman())
    assert not is_mock("foobar")
    assert not is_mock(Mock(spec=BittySnowman))
    assert not is_mock(MagicMock(spec=BittySnowman))


def test_is_mock_with_positive_cases():
    assert is_mock(Mock())
    assert is_mock(MagicMock())
    assert is_mock(NonCallableMock())
    assert is_mock(NonCallableMagicMock())


class Target:
    def __init__(self, a, b):
        pass

    def method(self, a, b):
        pass


@pytest.mark.parametrize("target", [Target, Target(1, 2).method])
@pytest.mark.parametrize(
    "args,kwargs,expected",
    [
        ((), {}, set("ab")),
        ((1,), {}, set("b")),
        ((1, 2), {}, set()),
        ((), dict(a=1), set("b")),
        ((), dict(b=2), set("a")),
        ((), dict(a=1, b=2), set()),
    ],
)
def test_required_args(target, args, kwargs, expected):
    # Mostly checking that `self` (and only self) is correctly excluded
    assert required_args(target, args, kwargs) == expected


def test_can_handle_unicode_identifier_in_same_line_as_lambda_def():
    # fmt: off
    pi = "π"; is_str_pi = lambda x: x == pi  # noqa: E702
    # fmt: on
    assert get_pretty_function_description(is_str_pi) == "lambda x: x == pi"


def test_can_render_lambda_with_no_encoding(monkeypatch):
    is_positive = lambda x: x > 0

    # Monkey-patching out the `detect_encoding` method here means
    # that our reflection can't detect the encoding of the source file, and
    # has to fall back to assuming it's ASCII.

    monkeypatch.setattr(reflection, "detect_encoding", None)
    assert get_pretty_function_description(is_positive) == "lambda x: x > 0"


def test_does_not_crash_on_utf8_lambda_without_encoding(monkeypatch):
    # Monkey-patching out the `detect_encoding` method here means
    # that our reflection can't detect the encoding of the source file, and
    # has to fall back to assuming it's ASCII.

    monkeypatch.setattr(reflection, "detect_encoding", None)
    # fmt: off
    pi = "π"; is_str_pi = lambda x: x == pi  # noqa: E702
    # fmt: on
    assert get_pretty_function_description(is_str_pi) == "lambda x: <unknown>"


def test_too_many_posargs_fails():
    with pytest.raises(TypeError):
        st.times(time.min, time.max, st.none(), st.none()).validate()


def test_overlapping_posarg_kwarg_fails():
    with pytest.raises(TypeError):
        st.times(time.min, time.max, st.none(), timezones=st.just(None)).validate()


def test_inline_given_handles_self():
    # Regression test for https://github.com/HypothesisWorks/hypothesis/issues/961
    class Cls:
        def method(self, **kwargs):
            assert isinstance(self, Cls)
            assert kwargs["k"] is sentinel

    sentinel = object()
    given(k=st.just(sentinel))(Cls().method)()


def logged(f):
    @wraps(f)
    def wrapper(*a, **kw):
        # print("I was called")
        return f(*a, **kw)

    return wrapper


class Bar:
    @logged
    def __init__(self, i: int):
        pass


@given(st.builds(Bar))
def test_issue_2495_regression(_):
    """See https://github.com/HypothesisWorks/hypothesis/issues/2495"""


@pytest.mark.skipif(
    sys.version_info[:2] >= (3, 11),
    reason="handled upstream in https://github.com/python/cpython/pull/92065",
)
def test_error_on_keyword_parameter_name():
    def f(source):
        pass

    f.__signature__ = Signature(
        parameters=[Parameter("from", Parameter.KEYWORD_ONLY)],
        return_annotation=Parameter.empty,
    )

    with pytest.raises(ValueError, match="SyntaxError because `from` is a keyword"):
        get_signature(f)


def test_param_is_called_within_func():
    def f(any_name):
        any_name()

    assert is_first_param_referenced_in_function(f)


def test_param_is_called_within_subfunc():
    def f(any_name):
        def f2():
            any_name()

    assert is_first_param_referenced_in_function(f)


def test_param_is_not_called_within_func():
    def f(any_name):
        pass

    assert not is_first_param_referenced_in_function(f)


def test_param_called_within_defaults_on_error():
    # Create a function object for which we cannot retrieve the source.
    f = compile("lambda: ...", "_.py", "eval")
    assert is_first_param_referenced_in_function(f)


def _prep_source(*pairs):
    return [
        pytest.param(dedent(x).strip(), dedent(y).strip().encode(), id=f"case-{i}")
        for i, (x, y) in enumerate(pairs)
    ]


@pytest.mark.parametrize(
    "src, clean",
    _prep_source(
        ("", ""),
        ("def test(): pass", "def test(): pass"),
        ("def invalid syntax", "def invalid syntax"),
        ("def also invalid(", "def also invalid("),
        (
            """
            @example(1)
            @given(st.integers())
            def test(x):
                # line comment
                assert x  # end-of-line comment


                "Had some blank lines above"
            """,
            """
            def test(x):
                assert x
                "Had some blank lines above"
            """,
        ),
        (
            """
            def      \\
                f(): pass
            """,
            """
            def\\
                f(): pass
            """,
        ),
        (
            """
            @dec
            async def f():
                pass
            """,
            """
            async def f():
                pass
            """,
        ),
    ),
)
def test_clean_source(src, clean):
    assert reflection._clean_source(src).splitlines() == clean.splitlines()


def test_overlong_repr_warns():
    with pytest.warns(HypothesisWarning, match="overly large"):
        repr(LazyStrategy(st.one_of, [st.none()] * 10000, {}))
