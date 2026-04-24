RELEASE_TYPE: patch

This patch fixes an internal :class:`AssertionError` in the ``explain``
shrinking phase (:issue:`4708`), introduced in :version:`6.149.0`.  The
assertion was triggered when a strategy inside a composite drew from
:func:`~hypothesis.strategies.just` applied to a fresh instance of a
user-defined class, because this causes the enclosing strategy to have a
different label on each test invocation.
