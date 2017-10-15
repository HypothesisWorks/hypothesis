RELEASE_TYPE: patch

This patch adds :PEP:`484` type hints to Hypothesis, on an experimental basis.
There is no user-visible impact in Hypothesis itself, but if you are using Mypy
with the ``follow_imports`` option you *might* see better results from
Hypothesis.
