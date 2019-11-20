RELEASE_TYPE: patch

This patch disables our :pypi:`pytest` plugin when running on versions
of :pypi:`pytest` before 4.3, the oldest our plugin supports.
Note that at time of writing the Pytest developers only support 4.6 and later!

Hypothesis *tests* using :func:`@given() <hypothesis.given>` work on any
test runner, but our integrations to e.g. avoid example database collisions
when combined with ``@pytest.mark.parametrize`` eventually drop support
for obsolete versions.
