RELEASE_TYPE: patch

This patch refactors ``width`` handling in :func:`~hypothesis.strategies.floats`;
you may notice small performance improvements but the main purpose is to
enable work on :issue:`1704` (improving shrinking of bounded floats).
