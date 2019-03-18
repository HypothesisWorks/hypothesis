RELEASE_TYPE: minor

This release makes it an explicit error to call
:func:`floats(min_value=inf, exclude_min=True) <hypothesis.strategies.floats>` or
:func:`floats(max_value=-inf, exclude_max=True) <hypothesis.strategies.floats>`,
as there are no possible values that can be generated (:issue:`1859`).
