RELEASE_TYPE: patch

This patch updates the type annotations for :func:`@given <hypothesis.given>`
so that type-checkers will warn on mixed positional and keyword arguments,
as well as fixing :issue:`3296`.
