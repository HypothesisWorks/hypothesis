RELEASE_TYPE: minor

This release defines ``__bool__()`` on :class:`~hypothesis.strategies.SearchStrategy`.
It always returns ``True``, like before, but also emits a warning to help with
cases where you intended to draw a value (:issue:`3463`).
