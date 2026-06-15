RELEASE_TYPE: patch

When using an alternative backend (such as :pypi:`hypothesis-crosshair`),
Hypothesis no longer emits a ``test_case`` observation for an iteration that the
backend aborts via ``BackendCannotProceed`` *before the test body runs*.
Previously such an iteration -- for example when the crosshair backend has
exhausted its search paths -- could surface as a spurious, draw-less ``passed``
observation with an empty representation, even though the engine already
discards the iteration entirely.
