RELEASE_TYPE: patch

This release improves shrink quality by allowing Hypothesis to automatically learn new shrink passes
for difficult to shrink tests.

The automatic learning is not currently accessible in user code (it still needs significant work
on robustness and performance before it is ready for that), but this release includes learned
passes that should improve shrinking quality for tests which use any of the :func:`~hypothesis.strategies.text`,:func:`~hypothesis.strategies.floats`,:func:`~hypothesis.strategies.datetimes`,,:func:`~hypothesis.strategies.emails`, and :func:`~hypothesis.strategies.complex_numbers` strategies.
