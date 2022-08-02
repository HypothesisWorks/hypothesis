RELEASE_TYPE: patch

This patch makes ``FailedHealthCheck`` and ``DeadlineExceeded`` exceptions
picklable, for compatibility with Django's parallel test runner (:issue:`3426`).
