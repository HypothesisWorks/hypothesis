RELEASE_TYPE: patch

This is a bugfix release for :issue:`739`, where bounds for
:func:`~hypothesis.strategies.fractions` or floating-point
:func:`~hypothesis.strategies.decimals` were not properly converted to
integers before passing them to the integers strategy.
This excluded some values that should have been possible, and could
trigger internal errors if the bounds lay between adjacent integers.

You can now bound :func:`~hypothesis.strategies.fractions` with two
arbitrarily close fractions.

It is now an explicit error to supply a min_value, max_value, and
max_denominator to :func:`~hypothesis.strategies.fractions` where the value
bounds do not include a fraction with denominator at most max_denominator.
