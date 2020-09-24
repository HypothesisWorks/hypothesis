RELEASE_TYPE: minor

This release upgrades the :func:`~hypothesis.extra.numpy.from_dtype` strategy
to pass optional ``**kwargs`` to the inferred strategy, and upgrades the
:func:`~hypothesis.extra.numpy.arrays` strategy to accept an ``elements=kwargs``
dict to pass through to :func:`~hypothesis.extra.numpy.from_dtype`.

``arrays(floating_dtypes(), shape, elements={"min_value": -10, "max_value": 10})``
is a particularly useful pattern, as it allows for any floating dtype without
triggering the roundoff warning for smaller types or sacrificing variety for
larger types (:issue:`2552`).
