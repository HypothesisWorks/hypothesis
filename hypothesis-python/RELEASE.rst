RELEASE_TYPE: patch

This patch automatically disables the :obj:`~hypothesis.HealthCheck.differing_executors`
health check for methods which are also pytest parametrized tests, because
those were mostly false alarms (:issue:`3733`).
