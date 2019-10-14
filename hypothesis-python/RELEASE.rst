RELEASE_TYPE: patch

This release changes how Hypothesis checks if a parameter to a test function is a mock object.
It is unlikely to have any noticeable effect, but may result in a small performance improvement,
especially for test functions where a mock object is being passed as the first argument.
