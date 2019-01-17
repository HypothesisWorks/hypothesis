RELEASE_TYPE: patch

This patch fixes :issue:`1387`, where bounded :func:`~hypothesis.strategies.integers`
with a very large range would almost always generate very large numbers.
Now, we usually use the same tuned distribution as unbounded
:func:`~hypothesis.strategies.integers`.
