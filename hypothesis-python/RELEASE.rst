RELEASE_TYPE: patch

Warn in :func:`~hypothesis.strategies.from_type` if the inferred strategy
has no variation (always returning default instances). Also ensures
variation in numpy data types by inferring h.extras.numpy.from_dtype().
