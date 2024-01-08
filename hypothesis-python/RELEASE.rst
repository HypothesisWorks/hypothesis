RELEASE_TYPE: patch

This patch adds a new environment variable ``HYPOTHESIS_EXPERIMENTAL_OBSERVABILITY_NOCOVER``,
which turns on :doc:`observability <observability>` data collection without collecting
code coverage data, which may be faster on Python 3.11 and earlier.

Thanks to Harrison Goldstein for reporting and fixing :issue:`3821`.
