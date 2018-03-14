RELEASE_TYPE: patch

This release allows :func:`~hypothesis.strategies.decimals` to handle inputs
which previously caused serious performance problems (:issue:`838`).

- ``Decimal(10) ** 999999`` is a valid bound for the decimals strategy,
  but caused problems when it was internally cast to an integer. We now use
  a variety of tricks including rescaling values and multi-step generation
  to handle very large or small values correctly *and* efficiently.
- Using very precise bounds would generate examples with that many digits of
  precision.  This could easily happen by accident - eg.
  ``Decimal(1).next_minus()`` may have over a million decimal places - so we
  now use similar tricks to consider fewer digits of the bounds internally.
