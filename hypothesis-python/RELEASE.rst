RELEASE_TYPE: patch

Fixed :func:`~hypothesis.strategies.from_type` support for
:pep:`604` union types, like ``int | None`` (:issue:`3255`).
