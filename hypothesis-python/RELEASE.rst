RELEASE_TYPE: patch

This patch allows Hypothesis to run in environments that do not specify
a ``__file__``, such as a :mod:`python:zipapp` (:issue:`2196`).
