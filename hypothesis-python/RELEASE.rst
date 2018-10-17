RELEASE_TYPE: patch

This patch fixes the internals for :func:`~hypothesis.strategies.floats`
and :func:`~hypothesis.strategies.complex_numbers` with one bound.
Such strategies now shrink in the same way as unconstrained numbers -
by simplifying the fractional part, then shrinking as integers towards
zero.
