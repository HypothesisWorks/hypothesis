RELEASE_TYPE: minor

This release deprecates the ``average_size`` argument to
:func:`~hypothesis.strategies.lists` and other collection strategies.

The ``average_size`` argument was treated as a hint about the distribution
of examples from a strategy.  In turn, this is a remnant of earlier versions
of Hypothesis with a different conceptual model and much weaker engine for
generating and shrinking examples.  More recent strategies simply describe
what constitutes a valid example, and let the internals handle the rest.

``average_size`` is immediately discarded internally, so you can simply delete
it wherever it appears in your tests without changing their behaviour at all.
