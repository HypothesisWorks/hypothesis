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

import sys
from copy import deepcopy
from functools import partial

import pytest

from hypothesis.internal.compat import PY2, PY3, FullArgSpec, getfullargspec
from hypothesis.internal.reflection import (
    arg_string,
    convert_keyword_arguments,
    convert_positional_arguments,
    define_function_signature,
    fully_qualified_name,
    function_digest,
    get_pretty_function_description,
    is_mock,
    proxies,
    required_args,
    source_exec_as_module,
    unbind_method,
)
from tests.common.utils import raises

try:
    from unittest.mock import MagicMock, Mock, NonCallableMagicMock, NonCallableMock
except ImportError:
    from mock import MagicMock, Mock, NonCallableMagicMock, NonCallableMock


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


def test_populates_defaults():
    def bar(x=[], y=1):
        pass

    assert convert_keyword_arguments(bar, (), {}) == (([], 1), {})
    assert convert_keyword_arguments(bar, (), {"y": 42}) == (([], 42), {})
    do_conversion_test(bar, (), {})
    do_conversion_test(bar, (1,), {})


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

    with raises(TypeError) as e:
        convert_keyword_arguments(foo, (1,), {"b": 1})
    assert "keyword" in e.value.args[0]

    with raises(TypeError) as e2:
        convert_keyword_arguments(foo, (1,), {"b": 1, "c": 2})
    assert "keyword" in e2.value.args[0]


def test_positional_errors_if_too_many_args():
    def foo(a):
        pass

    with raises(TypeError) as e:
        convert_positional_arguments(foo, (1, 2), {})
    assert "2 given" in e.value.args[0]


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

    with raises(TypeError) as e:
        convert_positional_arguments(foo, (), {"b": 1})
    assert "unexpected keyword argument" in e.value.args[0]


def test_positional_errors_if_given_duplicate_kwargs():
    def foo(a):
        pass

    with raises(TypeError) as e:
        convert_positional_arguments(foo, (2,), {"a": 1})
    assert "multiple values" in e.value.args[0]


def test_names_of_functions_are_pretty():
    assert (
        get_pretty_function_description(test_names_of_functions_are_pretty)
        == "test_names_of_functions_are_pretty"
    )


class Foo(object):
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

    assert arg_string(foo, (1, 2, 3, 4, 5), {}) == "c=1, a=2, b=3, f=4, a1=5"
    assert (
        arg_string(foo, (1, 2), {"b": 3, "f": 4, "a1": 5}) == "c=1, a=2, b=3, f=4, a1=5"
    )


def test_varkwargs_are_sorted_and_after_real_kwargs():
    def foo(d, e, f, **kwargs):
        pass

    assert (
        arg_string(foo, (), {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6})
        == "d=4, e=5, f=6, a=1, b=2, c=3"
    )


def test_varargs_come_without_equals():
    def foo(a, *args):
        pass

    assert arg_string(foo, (1, 2, 3, 4), {}) == "2, 3, 4, a=1"


def test_can_mix_varargs_and_varkwargs():
    def foo(*args, **kwargs):
        pass

    assert arg_string(foo, (1, 2, 3), {"c": 7}) == "1, 2, 3, c=7"


def test_arg_string_does_not_include_unprovided_defaults():
    def foo(a, b, c=9, d=10):
        pass

    assert arg_string(foo, (1,), {"b": 1, "d": 11}) == "a=1, b=1, d=11"


class A(object):
    def f(self):
        pass

    def g(self):
        pass


class B(A):
    pass


class C(A):
    def f(self):
        pass


def test_unbind_gives_parent_class_function():
    assert unbind_method(B().f) == unbind_method(A.f)


def test_unbind_distinguishes_different_functions():
    assert unbind_method(A.f) != unbind_method(A.g)


def test_unbind_distinguishes_overridden_functions():
    assert unbind_method(C().f) != unbind_method(A.f)


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
def test_copying_preserves_argspec(f):
    af = getfullargspec(f)
    t = define_function_signature("foo", "docstring", af)(universal_acceptor)
    at = getfullargspec(t)
    assert af.args == at.args
    assert af.varargs == at.varargs
    assert af.varkw == at.varkw
    assert len(af.defaults or ()) == len(at.defaults or ())
    assert af.kwonlyargs == at.kwonlyargs
    assert af.kwonlydefaults == at.kwonlydefaults
    assert af.annotations == at.annotations


def test_name_does_not_clash_with_function_names():
    def f():
        pass

    @define_function_signature("f", "A docstring for f", getfullargspec(f))
    def g():
        pass

    g()


def test_copying_sets_name():
    f = define_function_signature(
        "hello_world", "A docstring for hello_world", getfullargspec(has_two_args)
    )(universal_acceptor)
    assert f.__name__ == "hello_world"


def test_copying_sets_docstring():
    f = define_function_signature(
        "foo", "A docstring for foo", getfullargspec(has_two_args)
    )(universal_acceptor)
    assert f.__doc__ == "A docstring for foo"


def test_uses_defaults():
    f = define_function_signature(
        "foo", "A docstring for foo", getfullargspec(has_a_default)
    )(universal_acceptor)
    assert f(3, 2) == ((3, 2, 1), {})


def test_uses_varargs():
    f = define_function_signature(
        "foo", "A docstring for foo", getfullargspec(has_varargs)
    )(universal_acceptor)
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
        FullArgSpec(
            args=("f",),
            varargs=None,
            varkw=None,
            defaults=None,
            kwonlyargs=[],
            kwonlydefaults=None,
            annotations={},
        ),
    )(accepts_everything)(1)

    define_function_signature(
        "hello",
        "A docstring for hello",
        FullArgSpec(
            args=(),
            varargs="f",
            varkw=None,
            defaults=None,
            kwonlyargs=[],
            kwonlydefaults=None,
            annotations={},
        ),
    )(accepts_everything)(1)

    define_function_signature(
        "hello",
        "A docstring for hello",
        FullArgSpec(
            args=(),
            varargs=None,
            varkw="f",
            defaults=None,
            kwonlyargs=[],
            kwonlydefaults=None,
            annotations={},
        ),
    )(accepts_everything)()

    define_function_signature(
        "hello",
        "A docstring for hello",
        FullArgSpec(
            args=("f", "f_3"),
            varargs="f_1",
            varkw="f_2",
            defaults=None,
            kwonlyargs=[],
            kwonlydefaults=None,
            annotations={},
        ),
    )(accepts_everything)(1, 2)


def test_define_function_signature_validates_arguments():
    with raises(ValueError):
        define_function_signature(
            "hello_world",
            None,
            FullArgSpec(
                args=["a b"],
                varargs=None,
                varkw=None,
                defaults=None,
                kwonlyargs=[],
                kwonlydefaults=None,
                annotations={},
            ),
        )


def test_define_function_signature_validates_function_name():
    with raises(ValueError):
        define_function_signature(
            "hello world",
            None,
            FullArgSpec(
                args=["a", "b"],
                varargs=None,
                varkw=None,
                defaults=None,
                kwonlyargs=[],
                kwonlydefaults=None,
                annotations={},
            ),
        )


class Container(object):
    def funcy(self):
        pass


def test_fully_qualified_name():
    assert (
        fully_qualified_name(test_copying_preserves_argspec)
        == "tests.cover.test_reflection.test_copying_preserves_argspec"
    )
    assert (
        fully_qualified_name(Container.funcy)
        == "tests.cover.test_reflection.Container.funcy"
    )
    assert (
        fully_qualified_name(fully_qualified_name)
        == "hypothesis.internal.reflection.fully_qualified_name"
    )


def test_qualname_of_function_with_none_module_is_name():
    def f():
        pass

    f.__module__ = None
    assert fully_qualified_name(f)[-1] == "f"


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
        (lambda a: a ** 2, (2,), 4),
        (lambda *a: a, [1, 2, 3], (1, 2, 3)),
    ],
)
def test_can_proxy_lambdas(func, args, expected):
    @proxies(func)
    def wrapped(*args, **kwargs):
        return func(*args, **kwargs)

    assert wrapped.__name__ == "<lambda>"
    assert wrapped(*args) == expected


class Snowman(object):
    def __repr__(self):
        return "☃"


class BittySnowman(object):
    def __repr__(self):
        return "☃"


def test_can_handle_unicode_repr():
    def foo(x):
        pass

    assert arg_string(foo, [Snowman()], {}) == "x=☃"
    assert arg_string(foo, [], {"x": Snowman()}) == "x=☃"


class NoRepr(object):
    pass


def test_can_handle_repr_on_type():
    def foo(x):
        pass

    assert arg_string(foo, [Snowman], {}) == "x=Snowman"
    assert arg_string(foo, [NoRepr], {}) == "x=NoRepr"


def test_can_handle_repr_of_none():
    def foo(x):
        pass

    assert arg_string(foo, [None], {}) == "x=None"
    assert arg_string(foo, [], {"x": None}) == "x=None"


if not PY3:

    def test_can_handle_non_unicode_repr_containing_non_ascii():
        def foo(x):
            pass

        assert arg_string(foo, [BittySnowman()], {}) == "x=☃"
        assert arg_string(foo, [], {"x": BittySnowman()}) == "x=☃"


def test_kwargs_appear_in_arg_string():
    def varargs(*args, **kwargs):
        pass

    assert "x=1" in arg_string(varargs, (), {"x": 1})


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


class Target(object):
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


# fmt: off
pi = "π"; is_str_pi = lambda x: x == pi  # noqa: E731
# fmt: on


def test_can_handle_unicode_identifier_in_same_line_as_lambda_def():
    assert get_pretty_function_description(is_str_pi) == "lambda x: x == pi"


@pytest.mark.skipif(PY2, reason="detect_encoding does not exist in Python 2")
def test_can_render_lambda_with_no_encoding():
    is_positive = lambda x: x > 0

    # Monkey-patching out the `tokenize.detect_encoding` method here means
    # that our reflection can't detect the encoding of the source file, and
    # has to fall back to assuming it's ASCII.
    import tokenize

    old_detect_encoding = tokenize.detect_encoding
    try:
        del tokenize.detect_encoding
        assert get_pretty_function_description(is_positive) == "lambda x: x > 0"
    finally:
        tokenize.detect_encoding = old_detect_encoding


@pytest.mark.skipif(PY2, reason="detect_encoding does not exist in Python 2")
def test_does_not_crash_on_utf8_lambda_without_encoding():
    # Monkey-patching out the `tokenize.detect_encoding` method here means
    # that our reflection can't detect the encoding of the source file, and
    # has to fall back to assuming it's ASCII.
    import tokenize

    old_detect_encoding = tokenize.detect_encoding
    try:
        del tokenize.detect_encoding
        assert get_pretty_function_description(is_str_pi) == "lambda x: <unknown>"
    finally:
        tokenize.detect_encoding = old_detect_encoding
