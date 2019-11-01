RELEASE_TYPE: patch

This release fixes :func:`~hypothesis.strategies.from_type` when used with
bounded or constrained :obj:`python:typing.TypeVar` objects (:issue:`2094`).

Previously, distinct typevars with the same constraints would be treated as all
single typevar, and in cases where a typevar bound was resolved to a union of
subclasses this could result in mixed types being generated for that typevar.
