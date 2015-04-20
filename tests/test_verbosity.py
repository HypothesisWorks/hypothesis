from contextlib import contextmanager

from hypothesis.settings import Settings, Verbosity
from hypothesis import find, given
from tests.common.utils import fails, capture_out
from hypothesis.reporting import with_reporter, default as default_reporter


@contextmanager
def capture_verbosity(level):
    with capture_out() as o:
        with with_reporter(default_reporter):
            with Settings(verbosity=level):
                yield o


def test_does_not_log_in_quiet_mode():
    with capture_verbosity(Verbosity.quiet) as o:
        @fails
        @given(int)
        def test_foo(x):
            assert False

        test_foo()
    assert not o.getvalue()


def test_includes_progress_in_verbose_mode():
    with capture_verbosity(Verbosity.verbose) as o:
        with Settings(verbosity=Verbosity.verbose):
            find([int], lambda x: sum(x) >= 1000000)

    out = o.getvalue()
    assert out
    assert 'Shrunk example' in out
    assert 'Found satisfying example' in out


def test_includes_intermediate_results_in_verbose_mode():
    with capture_verbosity(Verbosity.verbose) as o:
        @fails
        @given([int])
        def test_foo(x):
            assert sum(x) < 1000000

        test_foo()
    lines = o.getvalue().splitlines()
    print(lines)
    assert len([l for l in lines if 'example' in l]) > 2
    assert len([l for l in lines if 'AssertionError' in l])
