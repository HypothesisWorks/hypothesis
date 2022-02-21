RELEASE_TYPE: patch

This patch fixes a bug in stateful testing, where returning a single value
wrapped in :func:`~hypothesis.stateful.multiple` would be printed such that
the assigned variable was a tuple rather than the single element
(:issue:`3236`).
