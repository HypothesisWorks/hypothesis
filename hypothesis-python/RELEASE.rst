RELEASE_TYPE: minor

This release deprecates use of the global random number generator while drawing
from a strategy, because this makes test cases less diverse and prevents us
from reporting minimal counterexamples (:issue:`3810`).

If you see this new warning, you can get a quick fix by using
:func:`~hypothesis.strategies.randoms`; or use more idiomatic strategies
:func:`~hypothesis.strategies.sampled_from`, :func:`~hypothesis.strategies.floats`,
:func:`~hypothesis.strategies.integers`, and so on.

Note that the same problem applies to e.g. ``numpy.random``, but
for performance reasons we only check the stdlib :mod:`random` module -
ignoring even other sources passed to :func:`~hypothesis.register_random`.
