RELEASE_TYPE: patch

This release adds the strategy :func:`~hypothesis.extra.numpy.mutually_broadcastable_shapes`,
which generates multiple array shapes that are mutually broadcast-compatible with a
user-specified base-shape. This is a generalization of
:func:`~hypothesis.extra.numpy.broadcastable_shapes`.

