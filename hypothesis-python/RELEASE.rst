RELEASE_TYPE: patch

Hypothesis can now :ref:`show statistics <statistics>` when running
under :pypi:`pytest-xdist`.  Previously, statistics were only reported
when all tests were run in a single process (:issue:`700`).
