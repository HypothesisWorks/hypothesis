from hypothesis.utils.threading import ThreadLocal
import pytest


def test_threadlocal_setattr_and_getattr():
    threadlocal = ThreadLocal(a=1, b=2)
    assert threadlocal.a == 1
    assert threadlocal.b == 2
    # check that we didn't add attributes to the ThreadLocal instance itself
    # instead of its threading.local() variable
    assert set(threadlocal.__dict__) == {
        "_ThreadLocal__initialized",
        "_ThreadLocal__kwargs",
        "_ThreadLocal__threadlocal",
    }

    threadlocal.a = 3
    assert threadlocal.a == 3
    assert threadlocal.b == 2
    assert set(threadlocal.__dict__) == {
        "_ThreadLocal__initialized",
        "_ThreadLocal__kwargs",
        "_ThreadLocal__threadlocal",
    }


def test_nonexistent_getattr_raises():
    threadlocal = ThreadLocal(a=1)
    with pytest.raises(AttributeError):
        c = threadlocal.c


def test_nonexistent_setattr_raises():
    threadlocal = ThreadLocal(a=1)
    with pytest.raises(AttributeError):
        threadlocal.c = 2
