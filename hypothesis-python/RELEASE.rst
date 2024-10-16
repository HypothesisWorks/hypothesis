RELEASE_TYPE: patch

This patch fixes a regression from :ref:`version 6.115.2 <v6.115.2>` where generating values from :func:`~hypothesis.strategies.integers` with certain values for ``min_value`` and ``max_value`` would error.
