RELEASE_TYPE: minor

This release deprecates use of :func:`~hypothesis.assume` and ``reject()``
outside of property-based tests, because these functions work by raising a
special exception (:issue:`3743`).  It also fixes some type annotations
(:issue:`3753`).
