RELEASE_TYPE: patch

This patch improves :func:`~hypothesis.strategies.dates` shrinking, to simplify
year, month, and day like :func:`~hypothesis.strategies.datetimes` rather than
minimizing the number of days since 2000-01-01.
