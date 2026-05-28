RELEASE_TYPE: minor

:func:`~hypothesis.extra.numpy.from_dtype` now supports the variable-width
string dtype :attr:`numpy:numpy.dtypes.StringDType`, generating arbitrary
strings via :func:`~hypothesis.strategies.text` (:issue:`4039`).

Additionally, passing a dtype *class* such as ``np.dtypes.StringDType`` where an
instance like ``np.dtypes.StringDType()`` was expected now raises a clear error,
rather than the previous confusing message (or silent coercion to the object
dtype in :func:`~hypothesis.extra.numpy.arrays`).
