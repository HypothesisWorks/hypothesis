RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.extra.numpy.from_dtype` with long-precision
floating-point datatypes (typecode ``g``; see :func:`numpy:numpy.typename`).
