RELEASE_TYPE: minor

This release improves some "unhappy paths" when using Hypothesis
with the standard library :mod:`python:unittest` module:

- Applying :func:`@given <hypothesis.given>` to a non-test method which is
  overridden from :class:`python:unittest.TestCase`, such as ``setUp``,
  raises :attr:`a new health check <hypothesis.settings.not_a_test_method>`.
  (:issue:`991`)
- Using :meth:`~python:unittest.TestCase.subTest` within a test decorated
  with :func:`@given <hypothesis.given>` would leak intermediate results
  when tests were run under the :mod:`python:unittest` test runner.
  Individual reporting of failing subtests is now disabled during a test
  using :func:`@given <hypothesis.given>`.  (:issue:`1071`)
- :func:`@given <hypothesis.given>` is still not a class decorator, but the
  error message if you try using it on a class has been improved.

As a related improvement, using :class:`django:django.test.TestCase` with
:func:`@given <hypothesis.given>` instead of
:class:`hypothesis.extra.django.TestCase` raises an explicit error instead
of running all examples in a single database transaction.
