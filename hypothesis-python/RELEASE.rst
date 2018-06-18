RELEASE_TYPE: minor

This release improves validation of the ``alphabet`` argument to the
:func:`~hypothesis.strategies.text` strategy.  The following misuses
are now deprecated, and will be an error in a future version:

- passing an unordered collection (such as ``set('abc')``), which
  violates invariants about shrinking and reproducibility
- passing an alphabet sequence with elements that are not strings
- passing an alphabet sequence with elements that are not of length one,
  which violates any size constraints that may apply

Thanks to Sushobhit for adding these warnings (:issue:`1329`).