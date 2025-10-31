RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.extra.ghostwriter.binary_operation` to
include imports for :mod:`hypothesis.extra.numpy` strategies such as
:func:`~hypothesis.extra.numpy.arrays`, :func:`~hypothesis.extra.numpy.scalar_dtypes`,
and :func:`~hypothesis.extra.numpy.array_shapes` when ghostwriting tests for
functions with numpy array parameters (:issue:`4576`).
