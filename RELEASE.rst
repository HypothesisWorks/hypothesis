RELEASE_TYPE: patch

This release improves the handling of deadlines so that they act better with
the shrinking process. This fixes :issue:`892`.

This involves two changes:

1. The deadline is raised during the initial generation and shrinking, and then
   lowered to the set value for final replay. This restricts our attention to
   examples which exceed the deadline by a more significant margin, which
   increases their reliability.
2. When despite the above a test still becomes flaky because it is
   significantly faster on rerun than it was on its first run, the error
   message is now more explicit about the nature of this problem, and includes
   both the initial test run time and the new test run time.

In addition, this release also clarifies the documentation of the deadline
setting slightly to be more explicit about where it applies.

This work was funded by `Smarkets <https://smarkets.com/>`_.
