RELEASE_TYPE: patch

This patch fixes :issue:`2722`, where certain orderings of
:func:`~hypothesis.strategies.register_type_strategy`,
:class:`~python:typing.ForwardRef`, and :func:`~hypothesis.strategies.from_type`
could trigger an internal error.
