RELEASE_TYPE: major

This release removes the following strategies:

*  :func:`~hypothesis.strategies.choices` and
   :func:`~hypothesis.strategies.streaming` (both deprecated in 3.15.0).
   Their use should be replaced with direct use of the
   :func:`~hypothesis.strategies.data` strategy.
