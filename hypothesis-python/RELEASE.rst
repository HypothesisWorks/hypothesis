RELEASE_TYPE: patch

This patch fixes Hypothesis sometimes raising a ``Flaky`` error when generating collections of unique floats containing ``nan``. See :issue:`3926` for more details.
