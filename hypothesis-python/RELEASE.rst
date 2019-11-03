RELEASE_TYPE: patch

This patch ensures that the default value :func:`~hypothesis.extra.numpy.broadcastable_shapes`
chooses for ``max_dims`` is always valid (at most 32), even if you pass ``min_dims=32``.
