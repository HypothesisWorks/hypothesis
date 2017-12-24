RELEASE_TYPE: patch

This release changes the average bit length of values drawn from
:func:`~hypothesis.strategies.integers` to be much smaller. Additionally it
changes the shrinking order so that now size is considered before sign - e.g.
-1 will be preferred to +10.

The new internal format for integers required some changes to the minimizer to
make work well, so you may also see some improvements to example quality in
unrelated areas.
