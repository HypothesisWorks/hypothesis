RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.strategies.from_type` with
:mod:`abstract types <python:abc>` which have either required but
non-type-annotated arguments to ``__init__``, or where
:func:`~hypothesis.strategies.from_type` can handle some concrete
subclasses but not others.
