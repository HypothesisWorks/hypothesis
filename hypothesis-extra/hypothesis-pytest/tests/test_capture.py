from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pytest

pytest_plugins = str('pytester')

TESTSUITE = """
from hypothesis import given, Settings, Verbosity

@given(int, settings=Settings(verbosity=Verbosity.verbose))
def test_should_be_verbose(x):
    pass
"""

@pytest.mark.parametrize("capture,expected", [
    ('no', True),
    ('fd', False),
])
def test_output_without_capture(testdir, capture, expected):
    script = testdir.makepyfile(TESTSUITE)
    result = testdir.runpytest(script, '--verbose', '--capture', capture)
    out = '\n'.join(result.stdout.lines)
    assert 'test_should_be_verbose' in out
    assert ('Trying example' in out) == expected
    assert result.ret == 0
