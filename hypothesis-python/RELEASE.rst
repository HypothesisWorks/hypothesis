RELEASE_TYPE: patch

Account for time spent in garbage collection during tests, to avoid
flaky ``DeadlineExceeded`` errors as seen in :issue:`3975`. Also fixes
overcounting of stateful run times resulting from :issue:`3890`.
