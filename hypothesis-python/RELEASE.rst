RELEASE_TYPE: minor

Deprecate use of :func:`~hypothesis.assume` and :func:`~hypothesis.reject`
outside of property-based tests, because these functions work by raising a
special exception (:issue:`3743`).
