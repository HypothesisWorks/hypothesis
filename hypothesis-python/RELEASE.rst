RELEASE_TYPE: patch

This release fixes a small caching bug in Hypothesis internals that may under
some circumstances have resulted in a less diverse set of test cases being
generated than was intended.

Fixing this problem revealed some performance problems that could occur during targeted property based testing, so this release also fixes those. Targeted property-based testing should now be significantly faster in some cases,
but this may be at the cost of reduced effectiveness.
