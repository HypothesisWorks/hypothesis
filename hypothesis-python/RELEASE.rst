RELEASE_TYPE: minor

This release makes it an explicit error to apply :func:`~hypothesis.stateful.invariant`
to a :func:`~hypothesis.stateful.rule` or :func:`~hypothesis.stateful.initialize` rule
in :doc:`stateful testing <stateful>`.  Such a combination had unclear semantics,
especially in combination with :func:`~hypothesis.stateful.precondition`, and was never
meant to be allowed (:issue:`2681`).
