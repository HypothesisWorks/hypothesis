RELEASE_TYPE: patch

This patch improves the error message for :issue:`3016`, where :pep:`585`
builtin generics with self-referential forward-reference strings cannot be
resolved to a strategy by :func:`~hypothesis.strategies.from_type`.
