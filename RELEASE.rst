RELEASE_TYPE: patch

This is a yak shaving release, mostly concerned with our own tests.

While :func:`~python:inspect.getfullargspec` was documented as deprecated
in Python 3.5, it never actually emitted a warning.  Our code to silence
this (nonexistent) warning has therefore been removed.

We now run our tests with ``DeprecationWarning`` as an error, and made some
minor changes to our own tests as a result.  This required similar upstream
updates to :pypi:`coverage` and :pypi:`execnet` (a test-time dependency via
:pypi:`pytest-xdist`).

There is no user-visible change in Hypothesis itself, but we encourage you
to consider enabling deprecations as errors in your own tests.
