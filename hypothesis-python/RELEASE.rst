RELEASE_TYPE: patch

This release changes the order in which Hypothesis chooses parts of the test case
to shrink. For typical usage this should be a significant performance improvement on
large examples. It is unlikely to have a major impact on example quality, but where
it does change the result it should usually be an improvement.
