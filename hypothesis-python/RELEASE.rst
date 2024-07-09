RELEASE_TYPE: patch

This patch treats ``HypothesisWarning`` exceptions as fatal
failures during test execution, thus not reporting warnings
as inconsistent (flaky) when run with ``-Werror``.
