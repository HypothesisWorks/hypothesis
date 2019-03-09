RELEASE_TYPE: minor

This release deprecates :func:`~hypothesis.strategies.sampled_from` with empty
sequences.  This returns :func:`~hypothesis.strategies.nothing`, which gives a
clear error if used directly... but simply vanishes if combined with another
strategy.

Tests that silently generate less than expected are a serious problem for
anyone relying on them to find bugs, and we think reliability more important
than convenience in this case.
