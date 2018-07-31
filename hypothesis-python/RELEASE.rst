RELEASE_TYPE: minor

:func:`~hypothesis.extra.numpy.arrays` now checks that integer and float
values drawn from ``elements`` and ``fill`` strategies can be safely cast
to the dtype of the array, and emits a warning otherwise (:issue:`1385`).

Elements in the resulting array could previously violate constraints on
the elements strategy due to floating-point overflow or truncation of
integers to fit smaller types.
