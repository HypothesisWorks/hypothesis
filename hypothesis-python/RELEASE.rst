RELEASE_TYPE: patch

This patch gives Hypothesis it's own internal :class:`~random.Random` instance,
ensuring that test suites which reset the global random state don't induce
weird correlations between property-based tests (:issue:`2135`).
