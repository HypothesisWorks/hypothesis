RELEASE_TYPE: patch

This patch fixes two bugs (:issue:`944` and :issue:`1521`), where messages
about :func:`@seed <hypothesis.seed` did not check the current verbosity
setting, and the wrong settings were active while executing
:ref:`explicit examples <providing-explicit-examples>`.
