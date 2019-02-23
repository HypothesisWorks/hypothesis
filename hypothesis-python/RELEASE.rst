RELEASE_TYPE: patch

This changes the order in which Hypothesis runs certain operations during shrinking.
This should significantly decrease memory usage and speed up shrinking of large examples.
