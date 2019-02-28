RELEASE_TYPE: patch

This release allows Hypothesis to calculate a number of attributes of generated test cases lazily.
This should significantly reduce memory usage and modestly improve performance,
especially for large test cases.
