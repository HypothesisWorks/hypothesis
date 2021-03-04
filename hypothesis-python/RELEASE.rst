RELEASE_TYPE: patch

This patch fixes :issue:`2794`, where nesting :func:`~hypothesis.strategies.deferred`
strategies within :func:`~hypothesis.strategies.recursive` strategies could
trigger an internal assertion.  While it was always possible to get the same
results from a more sensible strategy, the convoluted form now works too.
