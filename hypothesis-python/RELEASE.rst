RELEASE_TYPE: minor

This release turns ``HealthCheck.return_value`` and ``HealthCheck.not_a_test_method``
into unconditional errors.  Passing them to ``suppress_health_check=`` is therefore a deprecated no-op.
(:issue:`3568`).  Thanks to Reagan Lee for the patch!

Separately, GraalPy can now run and pass most of the hypothesis test suite (:issue:`3587`).
