import numpy as np
import pytest
from hypothesis import given, find, strategy
from hypothesis.internal.compat import binary_type, text_type
from hypothesis.extra.numpy import arrays


STANDARD_TYPES = list(map(np.dtype, [
    'int8', 'int32', 'int64',
    'float', 'float32', 'float64',
    complex,
    bool, text_type, binary_type
]))


@pytest.mark.parametrize('t', STANDARD_TYPES)
def test_produces_instances(t):
    @given(t)
    def test_is_t(x):
        assert isinstance(x, t.type)
    test_is_t()


@given(arrays(float, ()))
def test_empty_dimensions_are_scalars(x):
    assert isinstance(x, np.dtype(float).type)


class Foo(object):
    pass


@given(arrays(Foo, ()))
def test_generates_composite_types_as_scalars(x):
    assert isinstance(x, Foo)


@given(arrays('uint32', (5, 5)))
def test_generates_unsigned_ints(x):
    assert (x >= 0).all()


def test_generates_and_minimizes():
    x = find(arrays(float, (2, 2)), lambda t: True)
    assert (x == np.zeros(shape=(2, 2), dtype=float)).all()


def test_can_minimize_large_arrays_easily():
    x = find(arrays('uint32', 1000), lambda t: t.any())
    assert x.sum() == 1


def test_can_minimize_float_arrays():
    x = find(arrays(float, 1000), lambda t: t.sum() >= 1.0)
    assert 1.0 <= x.sum() <= 1.01


@strategy.extend_static(Foo)
def sf(spec, settings):
    return strategy((), settings).map(lambda x: Foo())


def test_can_create_arrays_of_composite_types():
    arr = find(arrays(Foo, 100), lambda x: True)
    for x in arr:
        assert isinstance(x, Foo)
