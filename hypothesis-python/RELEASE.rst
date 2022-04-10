RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.strategies.from_type` on a :class:`~python:typing.TypedDict`
with complex annotations, defined in a file using ``from __future__ import annotations``.
Thanks to Katelyn Gigante for identifying and fixing this bug!