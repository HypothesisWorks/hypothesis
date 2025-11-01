RELEASE_TYPE: minor

This release adds support for :class:`~fractions.Fraction` objects as
``min_value`` and ``max_value`` bounds in :func:`~hypothesis.strategies.decimals`,
similar to how :func:`~hypothesis.strategies.integers` handles fractions (:issue:`4466`).

The conversion is only accepted when mathematically precise - fractions that
cannot be exactly represented as :class:`~decimal.Decimal` values (such as
``Fraction(1, 3)``) are rejected with a clear error message.
