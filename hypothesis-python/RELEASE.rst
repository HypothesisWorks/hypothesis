RELEASE_TYPE: patch

This release replaces the identifiers Hypothesis uses to refer to parts of a test case with integer indices.
This will result in significantly lower memory usage. It may either slow down or speed up shrinking,
depending on the nature of the problem.
