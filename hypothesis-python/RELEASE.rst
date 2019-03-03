RELEASE_TYPE: patch

This patch removes some overhead from :func:`~hypothesis.extra.numpy.arrays`
with a constant shape and dtype.  The resulting performance improvement is
modest, but worthwile for small arrays.
