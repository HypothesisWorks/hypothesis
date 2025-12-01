RELEASE_TYPE: minor

This release adds a ``min_leaves`` argument to :func:`~hypothesis.strategies.recursive`,
which ensures that generated recursive structures have at least the specified number
of leaf nodes (:issue:`4205`).
