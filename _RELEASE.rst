RELEASE_TYPE: major

This release removes the following strategies:

*  :func:`~hypothesis.strategies.streaming` (deprecated in 3.15.0).  Its use
   should be replaced with direct use of the
   :func:`~hypothesis.strategies.data` strategy.
