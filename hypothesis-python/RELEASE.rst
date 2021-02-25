RELEASE_TYPE: patch

This patch enables :func:`~hypothesis.strategies.register_type_strategy` for subclasses of
:class:`python:typing.TypedDict`.  Previously, :func:`~hypothesis.strategies.from_type`
would ignore the registered strategy (:issue:`2872`).

Thanks to Ilya Lebedev for identifying and fixing this bug!