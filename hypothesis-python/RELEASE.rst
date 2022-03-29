RELEASE_TYPE: patch

The Hypothesis pytest plugin was not outputting valid xunit2 nodes when ``--junit-xml`` was specified. This has been broken since Pytest 5.4, which changed the internal API for adding nodes to the junit report.

This also fixes the issue when using hypothesis with ``--junit-xml`` and ``pytest-xdist`` where the junit xml report would not be xunit2 compatible. Now, when using with ``pytest-xdist``, the junit report will just omit the ``<properties>`` node.

References:
* https://github.com/pytest-dev/pytest/issues/7767#issuecomment-1082436256
* https://github.com/pytest-dev/pytest/issues/1126#issuecomment-484581283
* :issue:`1935`

Thanks to Brandon Chinn for this bug fix!
