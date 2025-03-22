RELEASE_TYPE: patch

If a test raises a "skip" exception from a testing framework, like :func:`pytest:pytest.skip`, we no longer save the input which caused the skip exception to the :ref:`example database <database>`. We assume skip exceptions are an expected outcome of a test, and not something we should try to replay.

Also fixes an issue with realizing symbolic values provided by :ref:`alternative backends <alternative-backends>` when Hypothesis raises encounters an internal error in its engine.
