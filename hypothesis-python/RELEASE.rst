RELEASE_TYPE: patch

This patch improves the error message when :func:`~hypothesis.strategies.from_type`
fails to resolve a forward-reference inside a :class:`python:typing.Type`
such as ``Type["int"]`` (:issue:`2565`).
