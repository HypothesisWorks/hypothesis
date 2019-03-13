RELEASE_TYPE: patch

This release adds a micro-optimisation to how Hypothesis caches test cases.
This will cause a small improvement in speed and memory usage for large test cases,
but in most common scenarios it is unlikely to be noticeable.
