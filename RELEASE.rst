RELEASE_TYPE: patch

This release fixes :func:`builds(callable) <hypothesis.strategies.builds>` so that ``target`` can be used as a keyword argument for passing values to the target. The target itself can still be specified as a keyword argument, but that behavior is now deprecated. The target should be provided as the first positional argument.
