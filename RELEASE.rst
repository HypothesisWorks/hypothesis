RELEASE_TYPE: patch

This patch avoids creating debug statements when debugging is disabled.
Profiling suggests this is a 5-10% performance improvement (:issue:`1040`).
