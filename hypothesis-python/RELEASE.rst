RELEASE_TYPE: minor

This release adds the :func:`~hypothesis.extra.dpcontracts.fulfill` function,
which is designed for testing code that uses :pypi:`dpcontracts` 0.4 or later
for input validation.  This provides some syntactic sugar around use of
:func:`~hypothesis.assume`, to automatically filter out and retry calls that
cause a precondition check to fail (:issue:`1474`).
