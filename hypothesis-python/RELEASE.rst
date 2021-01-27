RELEASE_TYPE: patch

This release prevents a race condition inside :func:`~hypothesis.strategies.recursive` strategies.
The race condition occurs when the same :func:`~hypothesis.strategies.recursive` strategy is shared among tests
that are running in multiple threads (:issue:`2717`).
