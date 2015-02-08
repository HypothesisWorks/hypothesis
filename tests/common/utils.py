import contextlib
import sys
from io import StringIO
import pytest
from hypothesis.internal.utils.reflection import proxies


@contextlib.contextmanager
def capture_out():
    old_out = sys.stdout
    try:
        new_out = StringIO()
        sys.stdout = new_out
        yield new_out
    finally:
        sys.stdout = old_out


def fails_with(e):
    def accepts(f):
        @proxies(f)
        def inverted_test(*arguments, **kwargs):
            with pytest.raises(e):
                f(*arguments, **kwargs)
        return inverted_test
    return accepts

fails = fails_with(AssertionError)
