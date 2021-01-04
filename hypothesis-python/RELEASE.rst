RELEASE_TYPE: minor

This release adds the
:obj:`~hypothesis.HealthCheck.function_scoped_fixture` health check value,
which can be used to suppress the existing warning that appears when
:func:`@given <hypothesis.given>` is applied to a test that uses pytest
function-scoped fixtures.

(This warning exists because function-scoped fixtures only run once per
function, not once per example, which is usually unexpected and can cause
subtle problems.)

When this warning becomes a health check error in a future release, suppressing
it via Python warning settings will no longer be possible.
In the rare case that once-per-function behaviour is intended, it will still be
possible to use :obj:`~hypothesis.HealthCheck.function_scoped_fixture` to
opt out of the health check error for specific tests.
