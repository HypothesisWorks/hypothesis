RELEASE_TYPE: patch

When a test is executed concurrently from multiple threads, |DeadlineExceeded| is now disabled, since the Python runtime may decide to switch away from a thread for longer than |settings.deadline|, and Hypothesis cannot track execution time per-thread. See :issue:`4478`.
