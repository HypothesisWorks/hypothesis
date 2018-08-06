RELEASE_TYPE: patch

This release fixes a bug in :func:`~hypotheses.strategies.floats`, where
setting ``allow_infinity=False`` and only one of ``min_value`` and
``max_value`` would allow infinite values to be generated.
