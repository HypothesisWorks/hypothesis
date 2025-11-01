RELEASE_TYPE: patch

This patch fixes :issue:`4484`, ensuring that skip exceptions (such as
:class:`unittest.SkipTest` or ``pytest.skip()``) are now saved to the
:doc:`example database <data>` and replayed on subsequent test runs. Previously,
these examples were saved but immediately deleted during replay, requiring the
test to re-discover the skipping input each time.
