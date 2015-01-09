from hypothesis.internal.utils.reflection import convert_keyword_arguments
import pytest


def test_simple_conversion():
    def foo(a, b, c):
        pass

    assert convert_keyword_arguments(
        foo, (1, 2, 3), {}) == ((1, 2, 3), {})
    assert convert_keyword_arguments(
        foo, (), {'a': 3, 'b': 2, 'c': 1}) == ((3, 2, 1), {})


def test_populates_defaults():
    def bar(x=[], y=1):
        pass

    assert convert_keyword_arguments(bar, (), {}) == (([], 1), {})
    assert convert_keyword_arguments(bar, (), {'y': 42}) == (([], 42), {})


def test_leaves_unknown_kwargs_in_dict():
    def bar(x, **kwargs):
        pass

    assert convert_keyword_arguments(bar, (1,), {'foo': 'hi'}) == (
        (1,), {'foo': 'hi'}
    )
    assert convert_keyword_arguments(bar, (), {'x': 1, 'foo': 'hi'}) == (
        (1,), {'foo': 'hi'}
    )


def test_errors_on_bad_kwargs():
    def bar():
        pass

    with pytest.raises(TypeError):
        convert_keyword_arguments((), {"foo": 1})


def test_passes_varargs_correctly():
    def foo(*args):
        pass

    assert convert_keyword_arguments(foo, (1, 2, 3), {}) == ((1, 2, 3), {})
    assert convert_keyword_arguments(foo, (), {'args': (1, 2, 3)}) == (
        (1, 2, 3), {})


def test_errors_if_not_enough_args():
    def foo(a, b, c, d=1):
        pass

    with pytest.raises(TypeError):
        assert convert_keyword_arguments(foo, (1, 2), {'d': 4})
