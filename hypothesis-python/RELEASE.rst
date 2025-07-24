RELEASE_TYPE: patch

|HealthCheck.differing_executors| is no longer raised if a test is executed by different executors from different threads. |HealthCheck.differing_executors| will still be raised if a test is executed by different executors in the same thread.
