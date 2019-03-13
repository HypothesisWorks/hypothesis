RELEASE_TYPE: patch

This release removes some redundant code that was no longer needed but was still running a significant amount of computation and allocation on the hot path.
This should result in a modest speed improvement for most tests, especially those with large test cases.
