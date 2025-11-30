RELEASE_TYPE: patch

This patch improves the type annotations for :func:`~hypothesis.extra.numpy.basic_indices`.
The return type now accurately reflects the ``allow_ellipsis`` and ``allow_newaxis``
parameters, excluding ``EllipsisType`` or ``None`` from the union when those index
types are disabled (:issue:`4607`).

Additionally, :func:`~hypothesis.assume` now has overloaded type annotations:
``assume(True)`` returns ``Literal[True]``, while ``assume(False)`` and
``assume(None)`` return ``NoReturn``.
