RELEASE_TYPE: minor

This release improves validation of numeric bounds for some strategies.

- :func:`~hypothesis.strategies.integers` and :func:`~hypothesis.strategies.floats`
  now raise ``InvalidArgument`` if passed a ``min_value`` or ``max_value``
  which is not an instance of :class:`~python:numbers.Real`, instead of
  various internal errors.
- :func:`~hypothesis.strategies.floats` now converts its bounding values to
  the nearest float above or below the min or max bound respectively, instead
  of just casting to float.  The old behaviour was incorrect in that you could
  generate ``float(min_value)``, even when this was less than ``min_value``
  itself (possible with eg. fractions).
- When both bounds are provided to :func:`~hypothesis.strategies.floats` but
  there are no floats in the interval, such as ``[(2**54)+1 .. (2**55)-1]``,
  InvalidArgument is raised.
- :func:`~hypothesis.strategies.decimals` gives a more useful error message
  if passed a string that cannot be converted to :class:`~python:decimal.Decimal`
  in a context where this error is not trapped.

Code that previously **seemed** to work may be explicitly broken if there
were no floats between ``min_value`` and ``max_value`` (only possible with
non-float bounds), or if a bound was not a :class:`~python:numbers.Real`
number but still allowed in :obj:`python:math.isnan` (some custom classes
with a ``__float__`` method).
