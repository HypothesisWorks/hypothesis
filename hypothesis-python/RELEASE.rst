RELEASE_TYPE: patch

Add a health check that detects if the same test is executed
several times by :ref:`different executors<custom-function-execution>`.
This can lead to various difficult-to-debug problems.
