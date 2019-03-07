RELEASE_TYPE: minor

This release improves Hypothesis's to detect flaky tests, by noticing when the behaviour of the test changes between runs.
In particular this will notice many new cases where data generation depends on external state (e.g. external sources of randomness) and flag those as flaky sooner and more reliably.

The basis of this feature is a considerable reengineering of how Hypothesis stores its history of test cases,
so on top of this its memory usage should be considerably reduced.
