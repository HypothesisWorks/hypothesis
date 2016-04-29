# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

import sys
from copy import deepcopy
from functools import partial

from tests.common.utils import raises
from hypothesis.internal.compat import PY3, ArgSpec, getargspec
from hypothesis.internal.reflection import proxies, arg_string, \
    copy_argspec, unbind_method, eval_directory, function_digest, \
    fully_qualified_name, source_exec_as_module, \
    convert_keyword_arguments, convert_positional_arguments, \
    get_pretty_function_description


def do_conversion_test(f, args, kwargs):
    result = f(*args, **kwargs)

    cargs, ckwargs = convert_keyword_arguments(f, args, kwargs)
    assert result == f(*cargs, **ckwargs)

    cargs2, ckwargs2 = convert_positional_arguments(f, args, kwargs)
    assert result == f(*cargs2, **ckwargs2)


def test_simple_conversion():
    def foo(a, b, c):
        return (a, b, c)

    assert convert_keyword_arguments(
        foo, (1, 2, 3), {}) == ((1, 2, 3), {})
    assert convert_keyword_arguments(
        foo, (), {'a': 3, 'b': 2, 'c': 1}) == ((3, 2, 1), {})

    do_conversion_test(foo, (1, 0), {'c': 2})
    do_conversion_test(foo, (1,), {'c': 2, 'b': 'foo'})


def test_populates_defaults():
    def bar(x=[], y=1):
        pass

    assert convert_keyword_arguments(bar, (), {}) == (([], 1), {})
    assert convert_keyword_arguments(bar, (), {'y': 42}) == (([], 42), {})
    do_conversion_test(bar, (), {})
    do_conversion_test(bar, (1,), {})


def test_leaves_unknown_kwargs_in_dict():
    def bar(x, **kwargs):
        pass

    assert convert_keyword_arguments(bar, (1,), {'foo': 'hi'}) == (
        (1,), {'foo': 'hi'}
    )
    assert convert_keyword_arguments(bar, (), {'x': 1, 'foo': 'hi'}) == (
        (1,), {'foo': 'hi'}
    )
    do_conversion_test(bar, (1,), {})
    do_conversion_test(bar, (), {'x': 1, 'y': 1})


def test_errors_on_bad_kwargs():
    def bar():
        pass    # pragma: no cover

    with raises(TypeError):
        convert_keyword_arguments(bar, (), {'foo': 1})


def test_passes_varargs_correctly():
    def foo(*args):
        pass

    assert convert_keyword_arguments(foo, (1, 2, 3), {}) == ((1, 2, 3), {})

    do_conversion_test(foo, (1, 2, 3), {})


def test_errors_if_keyword_precedes_positional():
    def foo(x, y):
        pass  # pragma: no cover
    with raises(TypeError):
        convert_keyword_arguments(foo, (1,), {'x': 2})


def test_errors_if_not_enough_args():
    def foo(a, b, c, d=1):
        pass  # pragma: no cover

    with raises(TypeError):
        convert_keyword_arguments(foo, (1, 2), {'d': 4})


def test_errors_on_extra_kwargs():
    def foo(a):
        pass  # pragma: no cover

    with raises(TypeError) as e:
        convert_keyword_arguments(foo, (1,), {'b': 1})
    assert 'keyword' in e.value.args[0]

    with raises(TypeError) as e2:
        convert_keyword_arguments(foo, (1,), {'b': 1, 'c': 2})
    assert 'keyword' in e2.value.args[0]


def test_positional_errors_if_too_many_args():
    def foo(a):
        pass

    with raises(TypeError) as e:
        convert_positional_arguments(foo, (1, 2), {})
    assert '2 given' in e.value.args[0]


def test_positional_errors_if_too_few_args():
    def foo(a, b, c):
        pass

    with raises(TypeError):
        convert_positional_arguments(foo, (1, 2), {})


def test_positional_does_not_error_if_extra_args_are_kwargs():
    def foo(a, b, c):
        pass

    convert_positional_arguments(foo, (1, 2), {'c': 3})


def test_positional_errors_if_given_bad_kwargs():
    def foo(a):
        pass

    with raises(TypeError) as e:
        convert_positional_arguments(foo, (), {'b': 1})
    assert 'unexpected keyword argument' in e.value.args[0]


def test_positional_errors_if_given_duplicate_kwargs():
    def foo(a):
        pass

    with raises(TypeError) as e:
        convert_positional_arguments(foo, (2,), {'a': 1})
    assert 'multiple values' in e.value.args[0]


def test_names_of_functions_are_pretty():
    assert get_pretty_function_description(
        test_names_of_functions_are_pretty
    ) == 'test_names_of_functions_are_pretty'


def test_can_have_unicode_in_lambda_sources():
    t = lambda x: 'é' not in x
    assert get_pretty_function_description(t) == (
        "lambda x: 'é' not in x"
    )


ordered_pair = (
    lambda right: [].map(
        lambda length: ()))


def test_can_get_descriptions_of_nested_lambdas_with_different_names():
    assert get_pretty_function_description(ordered_pair) == \
        'lambda right: [].map(lambda length: ())'


class Foo(object):

    @classmethod
    def bar(cls):
        pass  # pragma: no cover

    def baz(cls):
        pass  # pragma: no cover

    def __repr__(self):
        return 'SoNotFoo()'


def test_class_names_are_not_included_in_class_method_prettiness():
    assert get_pretty_function_description(Foo.bar) == 'bar'


def test_repr_is_included_in_bound_method_prettiness():
    assert get_pretty_function_description(Foo().baz) == 'SoNotFoo().baz'


def test_class_is_not_included_in_unbound_method():
    assert (
        get_pretty_function_description(Foo.baz)
        == 'baz'
    )


# Note: All of these no branch pragmas are because we don't actually ever want
# to call these lambdas. We're just inspecting their source.

def test_source_of_lambda_is_pretty():
    assert get_pretty_function_description(
        lambda x: True
    ) == 'lambda x: True'  # pragma: no cover


def test_variable_names_are_not_pretty():
    t = lambda x: True  # pragma: no cover
    assert get_pretty_function_description(t) == 'lambda x: True'


def test_does_not_error_on_dynamically_defined_functions():
    x = eval('lambda t: 1')
    get_pretty_function_description(x)


def test_collapses_whitespace_nicely():
    t = (
        lambda x,       y:           1  # pragma: no cover
    )
    assert get_pretty_function_description(t) == 'lambda x, y: 1'


def test_is_not_confused_by_tuples():
    p = (lambda x: x > 1, 2)[0]  # pragma: no cover

    assert get_pretty_function_description(p) == 'lambda x: x > 1'


def test_does_not_error_on_confused_sources():
    def ed(f, *args):
        return f

    x = ed(
        lambda x, y: (  # pragma: no cover
            x * y
        ).conjugate() == x.conjugate() * y.conjugate(), complex, complex)

    get_pretty_function_description(x)


def test_strips_comments_from_the_end():
    t = lambda x: 1  # pragma: no cover
    assert get_pretty_function_description(t) == 'lambda x: 1'


def test_does_not_strip_hashes_within_a_string():
    t = lambda x: '#'  # pragma: no cover
    assert get_pretty_function_description(t) == "lambda x: '#'"


def test_can_distinguish_between_two_lambdas_with_different_args():
    a, b = (lambda x: 1, lambda y: 2)  # pragma: no cover
    assert get_pretty_function_description(a) == 'lambda x: 1'
    assert get_pretty_function_description(b) == 'lambda y: 2'


def test_does_not_error_if_it_cannot_distinguish_between_two_lambdas():
    a, b = (lambda x: 1, lambda x: 2)  # pragma: no cover
    assert 'lambda x:' in get_pretty_function_description(a)
    assert 'lambda x:' in get_pretty_function_description(b)


def test_lambda_source_break_after_def_with_brackets():
    f = (lambda n:
         'aaa')

    source = get_pretty_function_description(f)
    assert source == "lambda n: 'aaa'"


def test_lambda_source_break_after_def_with_line_continuation():
    f = lambda n:\
        'aaa'

    source = get_pretty_function_description(f)
    assert source == "lambda n: 'aaa'"


def test_digests_are_reasonably_unique():
    assert (
        function_digest(test_simple_conversion) !=
        function_digest(test_does_not_error_on_dynamically_defined_functions)
    )


def test_digest_returns_the_same_value_for_two_calls():
    assert (
        function_digest(test_simple_conversion) ==
        function_digest(test_simple_conversion)
    )


def test_can_digest_a_built_in_function():
    import math
    assert function_digest(math.isnan) != function_digest(range)


def test_can_digest_a_unicode_lambda():
    function_digest(lambda x: '☃' in str(x))


def test_can_digest_a_function_with_no_name():
    def foo(x, y):
        pass
    function_digest(partial(foo, 1))


def test_arg_string_is_in_order():
    def foo(c, a, b, f, a1):
        pass

    assert arg_string(foo, (1, 2, 3, 4, 5), {}) == 'c=1, a=2, b=3, f=4, a1=5'
    assert arg_string(
        foo, (1, 2),
        {'b': 3, 'f': 4, 'a1': 5}) == 'c=1, a=2, b=3, f=4, a1=5'


def test_varkwargs_are_sorted_and_after_real_kwargs():
    def foo(d, e, f, **kwargs):
        pass

    assert arg_string(
        foo, (), {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6}
    ) == 'd=4, e=5, f=6, a=1, b=2, c=3'


def test_varargs_come_without_equals():
    def foo(a, *args):
        pass

    assert arg_string(foo, (1, 2, 3, 4), {}) == '2, 3, 4, a=1'


def test_can_mix_varargs_and_varkwargs():
    def foo(*args, **kwargs):
        pass

    assert arg_string(
        foo, (1, 2, 3), {'c': 7}
    ) == '1, 2, 3, c=7'


def test_arg_string_does_not_include_unprovided_defaults():
    def foo(a, b, c=9, d=10):
        pass

    assert arg_string(foo, (1,), {'b': 1, 'd': 11}) == 'a=1, b=1, d=11'


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


def test_copying_preserves_argspec():
    for f in [has_one_arg, has_two_args, has_varargs, has_kwargs]:
        af = getargspec(f)
        t = copy_argspec('foo', getargspec(f))(universal_acceptor)
        at = getargspec(t)
        assert af.args == at.args
        assert af.varargs == at.varargs
        assert af.keywords == at.keywords
        assert len(af.defaults or ()) == len(at.defaults or ())


def test_name_does_not_clash_with_function_names():
    def f():
        pass

    @copy_argspec('f', getargspec(f))
    def g():
        pass
    g()


def test_copying_sets_name():
    f = copy_argspec(
        'hello_world', getargspec(has_two_args))(universal_acceptor)
    assert f.__name__ == 'hello_world'


def test_uses_defaults():
    f = copy_argspec(
        'foo', getargspec(has_a_default))(universal_acceptor)
    assert f(3, 2) == ((3, 2, 1), {})


def test_uses_varargs():
    f = copy_argspec(
        'foo', getargspec(has_varargs))(universal_acceptor)
    assert f(1, 2) == ((1, 2), {})


DEFINE_FOO_FUNCTION = """
def foo(x):
    return x
"""


def test_exec_as_module_execs():
    m = source_exec_as_module(DEFINE_FOO_FUNCTION)
    assert m.foo(1) == 1


def test_exec_as_module_caches():
    assert (
        source_exec_as_module(DEFINE_FOO_FUNCTION) is
        source_exec_as_module(DEFINE_FOO_FUNCTION)
    )


def test_exec_leaves_sys_path_unchanged():
    old_path = deepcopy(sys.path)
    source_exec_as_module('hello_world = 42')
    assert sys.path == old_path


def test_copy_argspec_works_with_conflicts():
    def accepts_everything(*args, **kwargs):
        pass

    copy_argspec('hello', ArgSpec(
        args=('f',), varargs=None, keywords=None, defaults=None
    ))(accepts_everything)(1)

    copy_argspec('hello', ArgSpec(
        args=(), varargs='f', keywords=None, defaults=None
    ))(accepts_everything)(1)

    copy_argspec('hello', ArgSpec(
        args=(), varargs=None, keywords='f', defaults=None
    ))(accepts_everything)()

    copy_argspec('hello', ArgSpec(
        args=('f', 'f_3'), varargs='f_1', keywords='f_2', defaults=None
    ))(accepts_everything)(1, 2)


def test_copy_argspec_validates_arguments():
    with raises(ValueError):
        copy_argspec('hello_world', ArgSpec(
            args=['a b'], varargs=None, keywords=None, defaults=None))


def test_copy_argspec_validates_function_name():
    with raises(ValueError):
        copy_argspec('hello world', ArgSpec(
            args=['a', 'b'], varargs=None, keywords=None, defaults=None))


class Container(object):

    def funcy(self):
        pass


def test_fully_qualified_name():
    assert fully_qualified_name(test_copying_preserves_argspec) == \
        'tests.cover.test_reflection.test_copying_preserves_argspec'
    assert fully_qualified_name(Container.funcy) == \
        'tests.cover.test_reflection.Container.funcy'
    assert fully_qualified_name(fully_qualified_name) == \
        'hypothesis.internal.reflection.fully_qualified_name'


def test_qualname_of_function_with_none_module_is_name():
    def f():
        pass
    f.__module__ = None
    assert fully_qualified_name(f)[-1] == 'f'


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


class Snowman(object):

    def __repr__(self):
        return '☃'


class BittySnowman(object):

    def __repr__(self):
        return '☃'


def test_can_handle_unicode_repr():
    def foo(x):
        pass
    from hypothesis import settings
    with settings(strict=False):
        assert arg_string(foo, [Snowman()], {}) == 'x=☃'
        assert arg_string(foo, [], {'x': Snowman()}) == 'x=☃'


class NoRepr(object):
    pass


def test_can_handle_repr_on_type():
    def foo(x):
        pass
    assert arg_string(foo, [Snowman], {}) == 'x=Snowman'
    assert arg_string(foo, [NoRepr], {}) == 'x=NoRepr'


def test_can_handle_repr_of_none():
    def foo(x):
        pass

    assert arg_string(foo, [None], {}) == 'x=None'
    assert arg_string(foo, [], {'x': None}) == 'x=None'


if not PY3:
    def test_can_handle_non_unicode_repr_containing_non_ascii():
        def foo(x):
            pass

        assert arg_string(foo, [BittySnowman()], {}) == 'x=☃'
        assert arg_string(foo, [], {'x': BittySnowman()}) == 'x=☃'


def test_does_not_put_eval_directory_on_path():
    source_exec_as_module("hello = 'world'")
    assert eval_directory() not in sys.path


def varargs(*args, **kwargs):
    pass


def test_kwargs_appear_in_arg_string():
    assert 'x=1' in arg_string(varargs, (), {'x': 1})
