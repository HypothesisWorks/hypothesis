RELEASE_TYPE: patch

This patch improves the error message from the
:func:`~hypothesis.extra.pandas.data_frames` strategy when both the ``rows``
and ``columns`` arguments are given, but there is a missing entry in ``rows``
and the corresponding column has no ``fill`` value (:issue:`2678`).
