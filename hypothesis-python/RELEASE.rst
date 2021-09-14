RELEASE_TYPE: patch

This release deprecates use of ``max_dims > len(shape)`` when
``allow_newaxis == False`` in :func:`~hypothesis.extra.numpy.basic_indices`
(:issue:`3091`).
