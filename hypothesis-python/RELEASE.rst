RELEASE_TYPE: patch

This patch documents the :func:`~hypothesis.extra.numpy.from_dtype` function,
which infers a strategy for :class:`numpy:numpy.dtype`s.  This is used in
:func:`~hypothesis.extra.numpy.arrays`, but can also be used directly when
creating e.g. Pandas objects.
