RELEASE_TYPE: patch

This patch adds some :doc:`observability information <observability>`
about how many times predicates in :func:`~hypothesis.assume` or
:func:`~hypothesis.stateful.precondition` were satisfied, so that
downstream tools can warn you if some were *never* satisfied by
any test case.
