RELEASE_TYPE: patch

This patch updates the type annotations for :func:`~hypothesis.strategies.tuples` so 
that type-checkers require its arguments to be positional-only, and so that it no 
longer fails under pyright-strict mode (see :issue:`3348`).
