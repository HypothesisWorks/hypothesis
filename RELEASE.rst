RELEASE_TYPE: patch

This is a bugfix release for `~hypothesis.strategies.integers`.
Previously the strategy would hit an internal assertion if passed non-integer
bounds for ``min_value`` and ``max_value`` that had no integers between them.
The strategy now raises InvalidArgument instead.
