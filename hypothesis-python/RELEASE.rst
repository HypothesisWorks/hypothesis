RELEASE_TYPE: patch

This release fixes :issue:`2507`, where lazy evaluation meant that the
values drawn from a :func:`~hypothesis.strategies.sampled_from` strategy
could depend on mutations of the sampled sequence that happened after
the strategy was constructed.
