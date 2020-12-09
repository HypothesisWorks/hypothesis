RELEASE_TYPE: patch

This patch refactors :class:`hypothesis.settings` to use type-annotated
keyword arguments instead of ``**kwargs``, which makes tab-completion
much more useful - as well as type-checkers like :pypi:`mypy`.
