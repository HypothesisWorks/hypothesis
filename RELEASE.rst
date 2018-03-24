RELEASE_TYPE: minor

This release deprecates the ``average_size`` argument to
:func:`~hypothesis.strategies.lists` and other collection strategies.
You should simply delete it wherever it was used in your tests, as it
no longer has any effect.

In early versions of Hypothesis, the ``average_size`` argument was treated
as a hint about the distribution of examples from a strategy.  Subsequent
improvements to the conceptual model and the engine for generating and
shrinking examples mean it is more effective to simply describe what
constitutes a valid example, and let our internals handle the distribution.
