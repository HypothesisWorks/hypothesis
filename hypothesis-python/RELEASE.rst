RELEASE_TYPE: minor

This release makes it an explicit error to call
:func:`floats(min_value=inf, exclude_min=True) <hypothesis.strategies.floats>` or
:func:`floats(max_value=-inf, exclude_max=True) <hypothesis.strategies.floats>`,
as there are no possible values that can be generated (:issue:`1859`).

:func:`floats(min_value=0.0, max_value=-0.0) <hypothesis.strategies.floats>`
is now deprecated.  While `0. == -0.` and we could thus generate either if
comparing by value, violating the sequence ordering of floats is a special
case we don't want or need.
