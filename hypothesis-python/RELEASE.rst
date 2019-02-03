RELEASE_TYPE: minor

This release adds ``exclude_min`` and ``exclude_max`` arguments to
:func:`~hypothesis.strategies.floats`, so that you can easily generate values from
`open or half-open intervals <https://en.wikipedia.org/wiki/Interval_(mathematics)>`_
(:issue:`1622`).
