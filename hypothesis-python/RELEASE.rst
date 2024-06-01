RELEASE_TYPE: patch

Account for time spent in garbage collection during tests, to avoid
flaky ``DeadlineExceeded`` errors as seen in :issue:`3975`.

Also fixes overcounting of stateful run times,
a minor observability bug dating to :ref:`version 6.98.9 <v6.98.9>`
(:pull:`3890`).
