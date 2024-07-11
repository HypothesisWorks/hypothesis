RELEASE_TYPE: minor

This release improves support for unions of :pypi:`numpy` dtypes such as
``np.float64 | np.complex128`` in :func:`~hypothesis.strategies.from_type`
and :func:`~hypothesis.extra.numpy.arrays` (:issue:`4041`).
