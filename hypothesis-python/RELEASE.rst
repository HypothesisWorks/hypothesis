RELEASE_TYPE: patch

This release ensures that :func:`~hypothesis.extra.numpy.broadcastable_shapes` can never generate
a value for ``max_dims`` that exceeds 32. Automated tests for this strategy were also made more robust.
