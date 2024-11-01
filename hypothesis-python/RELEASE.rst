RELEASE_TYPE: patch

When Hypothesis replays examples from its test database that it knows were previously fully shrunk it will no longer try to shrink them again.

This should significantly speed up development workflows for slow tests, as the shrinking could contribute a significant delay when rerunning the tests.

In some rare cases this may cause minor reductions in example quality. This was considered an acceptable tradeoff for the improved test runtime.
