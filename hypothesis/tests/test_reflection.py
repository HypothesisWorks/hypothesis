from hypothesis.internal.utils.reflection import convert_keyword_arguments
import pytest


def do_conversion_test(f, args, kwargs):
    cargs, ckwargs = convert_keyword_arguments(f, args, kwargs)
    assert f(*args, **kwargs) == f(*cargs, **ckwargs)


def test_simple_conversion():
    def foo(a, b, c):
        return (a, b, c)

    assert convert_keyword_arguments(
        foo, (1, 2, 3), {}) == ((1, 2, 3), {})
    assert convert_keyword_arguments(
        foo, (), {'a': 3, 'b': 2, 'c': 1}) == ((3, 2, 1), {})

    do_conversion_test(foo, (1, 0), {'c': 2})
    do_conversion_test(foo, (1,), {'c': 2, 'b': "foo"})


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

    with pytest.raises(TypeError):
        convert_keyword_arguments(bar, (), {"foo": 1})


def test_passes_varargs_correctly():
    def foo(*args):
        pass

    assert convert_keyword_arguments(foo, (1, 2, 3), {}) == ((1, 2, 3), {})

    do_conversion_test(foo, (1, 2, 3), {})


def test_errors_if_keyword_precedes_positional():
    def foo(x, y):
        pass  # pragma: no cover
    with pytest.raises(TypeError):
        convert_keyword_arguments(foo, (1,), {'x': 2})


def test_errors_if_not_enough_args():
    def foo(a, b, c, d=1):
        pass  # pragma: no cover

    with pytest.raises(TypeError):
        convert_keyword_arguments(foo, (1, 2), {'d': 4})


def test_errors_on_extra_kwargs():
    def foo(a):
        pass  # pragma: no cover

    with pytest.raises(TypeError) as e:
        convert_keyword_arguments(foo, (1,), {'b': 1})
    assert 'keyword' in e.value[0]

    with pytest.raises(TypeError) as e2:
        convert_keyword_arguments(foo, (1,), {'b': 1, 'c': 2})
    assert 'keyword' in e2.value[0]
