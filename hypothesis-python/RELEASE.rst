RELEASE_TYPE: minor

This release adds a ``allow_noop=False`` argument to :func:`~hypothesis.target`.
If ``True``, calling it outside of an :func:`@given() <hypothesis.given>` test
becomes a no-op rather than an error, which is useful when writing custom
assertion helpers (:issue:`2581`).
