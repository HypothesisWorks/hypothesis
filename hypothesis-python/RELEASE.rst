RELEASE_TYPE: patch

When a test is executed concurrently from multiple threads, |HealthCheck.too_slow| is now disabled, since the Python runtime may decide to switch away from a thread for arbitrarily long and Hypothesis cannot track execution time per-thread.
