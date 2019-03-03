RELEASE_TYPE: minor

This release adds the strategy :func:`~hypothesis.extra.numpy.valid_tuple_axes`,
which generates tuples of axis-indices that can be passed to the ``axis`` argument
in NumPy's sequential functions (e.g. :func:`numpy:numpy.sum`).