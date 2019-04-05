RELEASE_TYPE: patch

This release fixes a bug that prevented
:func:`~hypothesis.strategies.random_module`
from correctly restoring the previous state of the ``random`` module.

The random state was instead being restored to a temporary deterministic
state, which accidentally caused subsequent tests to see the same random values
across multiple test runs.
