pytest_plugins = 'pytester'


TESTSUITE = """
from hypothesis import given

@given(int)
def test_this_one_is_ok(x):
    pass

@given([int])
def test_always_sorted(xs):
    assert sorted(xs) == xs

@given([int])
def test_never_sorted(xs):
    assert sorted(xs) != xs
"""


def test_runs_reporting_hook(testdir):
    script = testdir.makepyfile(TESTSUITE)

    result = testdir.runpytest(
        '--hypothesis',
        script,
    )
    out = '\n'.join(result.stdout.lines)
    assert 'test_this_one_is_ok' in out
    assert 'Captured stdout call' not in out
    assert 'Falsifying example' in out
    assert result.ret != 0
