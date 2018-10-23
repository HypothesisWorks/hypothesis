RELEASE_TYPE: patch

Hypothesis now seeds and resets the global state of
:class:`np.random <numpy:numpy.random.RandomState>` for each
test case, to ensure that tests are reproducible.

This matches and complements the existing handling of the
:mod:`python:random` module - Numpy simply maintains an
independent PRNG for performance reasons.
