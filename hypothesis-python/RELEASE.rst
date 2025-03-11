RELEASE_TYPE: minor

This patch adds an :ref:`alternative backend <alternative-backends>` which draws randomness from ``/dev/urandom``. This is useful for users of `Antithesis <https://antithesis.com/>`_ who also have Hypothesis tests, allowing Antithesis mutation of ``/dev/urandom`` to drive Hypothesis generation.
