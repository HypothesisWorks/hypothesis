RELEASE_TYPE: patch

This patch fixes a very rare example database issue with file permissions.

When running a test that uses both :func:`@given <hypothesis.given>`
and ``pytest.mark.parametrize``, using :pypi:`pytest-xdist` on Windows,
with failing examples in the database, two attempts to read a file could
overlap and we caught ``FileNotFound`` but not other ``OSError``\ s.
