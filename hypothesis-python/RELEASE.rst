RELEASE_TYPE: patch

This release fixes :issue:`1813`, a bug introduced in :ref:`3.59.1 <v3.59.1>`,
which caused :py:meth:`~hypothesis.strategies.random_module` to no longer affect the body of the test:
Although Hypothesis would claim to be seeding the random module in fact tests would always run with a seed of zero.
