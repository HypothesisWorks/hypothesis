RELEASE_TYPE: patch

:func:`~hypothesis.strategies.nothing` is now typed as ``SearchStrategy[Never]``, because no value can ever be drawn from it. This may help type checkers statically determine that some code is not reachable.
