RELEASE_TYPE: minor

Warn in :func:`~hypothesis.strategies.from_type` if the inferred strategy
has no variation (always returning default instances). Also handles numpy
data types by calling :func:`~hypothesis.extra.numpy.from_dtype` on the
corresponding dtype, thus ensuring proper variation for these types.
