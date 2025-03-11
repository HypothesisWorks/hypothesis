RELEASE_TYPE: minor

This release adds a ``"hypothesis-urandom"`` :ref:`backend <alternative-backends>`, which draws randomness from ``/dev/urandom`` instead of Python's PRNG. This is useful for users of `Antithesis <https://antithesis.com/>`_ who also have Hypothesis tests, allowing Antithesis mutation of ``/dev/urandom`` to drive Hypothesis generation. We expect it to be strictly slower than the default backend for everyone else.

It can be enabled with ``@settings(backend="hypothesis-urandom")``.
