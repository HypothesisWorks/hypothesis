RELEASE_TYPE: patch

This patch further reduces Hypothesis' overhead for each test case, mostly by
saving and restoring the global random state once per test rather than once
per test case. For simple properties and strategies, generating test cases
takes up to a third less time; most tests will see a smaller improvement.
