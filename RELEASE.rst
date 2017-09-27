RELEASE_TYPE: patch

This release does some tidying in Hypothesis's settings:

*  The ``report_statistics`` is setting has been removed (which was never
   documented, and had no effect on behaviour).
*  The ``derandomize`` setting is now documented.
*  The ``derandomize``, ``perform_health_check`` and ``use_coverage`` settings
   now all error if passed a non-boolean value.
