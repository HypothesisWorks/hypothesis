RELEASE_TYPE: patch

This release fixes a small caching bug in Hypothesis internals that may under
some circumstances have resulted in a less diverse set of test cases being
generated than was intended.
