RELEASE_TYPE: patch

This patch fixes a bug that caused :func:`~hypothesis.strategies.integers`
to shrink towards negative values instead of positive values in some cases.
