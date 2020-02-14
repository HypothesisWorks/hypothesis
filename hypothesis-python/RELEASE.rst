RELEASE_TYPE: patch

This patch fixes :issue:`2351`, :func:`~hypothesis.extra.numpy.arrays` would
raise a confusing error if we inferred a strategy for ``datetime64`` or
``timedelta64`` values with varying time units.

We now infer an internally-consistent strategy for such arrays, and have a more
helpful error message if an inconsistent strategy is explicitly specified.
