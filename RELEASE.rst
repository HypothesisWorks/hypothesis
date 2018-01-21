RELEASE_TYPE: patch

This is a small refactoring release that changes how Hypothesis tracks some
information about the boundary of examples in its internal representation.

You are unlikely to see much difference in behaviour, but memory usage and
run time may both go down slightly during normal test execution, and when
failing Hypothesis might print its failing example slightly sooner.
