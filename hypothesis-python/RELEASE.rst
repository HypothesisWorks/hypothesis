RELEASE_TYPE: minor

This release adds :func:`~hypothesis.register_random`, which registers
``random.Random`` instances or compatible objects to be seeded and reset
by Hypothesis to ensure that test cases are deterministic.

We still recommend explicitly passing a ``random.Random`` instance from
:func:`~hypothesis.strategies.randoms` if possible, but registering a
framework-global state for Hypothesis to manage is better than flaky tests!
