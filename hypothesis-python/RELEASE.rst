RELEASE_TYPE: patch

This patch fixes a bug where :func:`~hypothesis.strategies.from_type` would error on certain types involving :class:`~python:typing.Protocol` (:issue:`4194`).
