RELEASE_TYPE: minor

The :func:`~hypothesis.extra.numpy.from_dtype` function no longer generates
``NaT`` ("not-a-time") values for the ``datetime64`` or ``timedelta64`` dtypes
if passed ``allow_nan=False`` (:issue:`3943`).
