RELEASE_TYPE: minor

This is a deprecation release for some health check related features.

The following are now deprecated:

* Passing :attr:`~hypothesis.HealthCheck.exception_in_generation` to
  :attr:`~hypothesis.settings.suppress_health_check`. This no longer does
  anything even when passed -  All errors that occur during data generation
  will now be immediately reraised rather than going through the health check
  mechanism.
* Passing :attr:`~hypothesis.HealthCheck.random_module` to
  :attr:`~hypothesis.settings.suppress_health_check`. This hasn't done anything
  for a long time, but was never explicitly deprecated. Hypothesis always seeds
  the random module when running tests, so this is no longer an error and
  suppressing it doesn't do anything.
* Passing non-:class:`~hypothesis.HealthCheck` values in
  :attr:`~hypothesis.settings.suppress_health_check`. This was previously
  allowed but never did anything useful.

In addition, passing a non-iterable value as :attr:`~hypothesis.settings.suppress_health_check`
will now raise an error immediately (it would never have worked correctly, but
it would previously have failed later).

This work was funded by `Smarkets <https://smarkets.com/>`_.
