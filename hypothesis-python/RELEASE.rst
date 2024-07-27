RELEASE_TYPE: patch

This patch fixes a rare internal error when using :func:`~hypothesis.strategies.integers` with a high number of examples and certain ``{min, max}_value`` parameters (:pull:`4059`).
