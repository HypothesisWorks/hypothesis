RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.strategies.from_type` and
:func:`~hypothesis.strategies.register_type_strategy` for
:obj:`python:typing.NewType` on Python 3.10, which changed the
underlying implementation (see :bpo:`44353` for details).
