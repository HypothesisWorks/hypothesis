RELEASE_TYPE: minor

This release fixes :doc:`stateful testing methods <stateful>` with multiple
:func:`~hypothesis.stateful.precondition` decorators.  Previously, only the
outer-most precondition was checked (:issue:`2681`).
