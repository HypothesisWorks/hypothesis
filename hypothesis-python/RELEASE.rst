RELEASE_TYPE: patch

Account for time spent in garbage collection during tests, to avoid
flaky DeadlineExceeded errors. Also fixes overcounting of stateful
run times, introduced in PR #3890.
