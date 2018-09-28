RELEASE_TYPE: patch

This patch fixes :issue:`1153`, where time spent reifying a strategy was
also counted in the time spent generating the first example.  Strategies
are now fully constructed and validated before the timer is started.
