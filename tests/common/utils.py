import contextlib
import sys
from io import StringIO


@contextlib.contextmanager
def capture_out():
    old_out = sys.stdout
    try:
        new_out = StringIO()
        sys.stdout = new_out
        yield new_out
    finally:
        sys.stdout = old_out
