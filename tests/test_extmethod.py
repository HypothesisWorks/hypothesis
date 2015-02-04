from hypothesis.internal.extmethod import ExtMethod
import pytest


def test_will_use_tightest_class():
    f = ExtMethod()

    @f.extend(object)
    def foo():
        return 0

    @f.extend(int)
    def bar():
        return 1

    assert f(object) == 0
    assert f(str) == 0
    assert f(int) == 1


def test_will_error_on_missing():
    f = ExtMethod()
    with pytest.raises(NotImplementedError):
        f(int)
