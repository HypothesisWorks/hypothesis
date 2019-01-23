RELEASE_TYPE: minor

This release deprecates ``HealthCheck.hung_test`` and disables the
associated runtime check for tests that ran for more than five minutes.
Such a check is redundant now that we enforce the ``deadline`` and
``max_examples`` setting, which can be adjusted independently.
