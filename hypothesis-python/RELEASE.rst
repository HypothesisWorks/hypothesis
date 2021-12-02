RELEASE_TYPE: patch

This patch fixes a bug in :func:`~hypothesis.extra.numpy.mutually_broadcastable_shapes`,
which restricted the patterns of singleton dimensions that could be generated for
dimensions that extended beyond ``base_shape`` (:issue:`3170`).
