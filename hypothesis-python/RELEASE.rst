RELEASE_TYPE: minor

This release :func:`registers <hypothesis.strategies.register_type_strategy>` the
remaining builtin types, and teaches :func:`~hypothesis.strategies.from_type` to
try resolving :class:`~python:typing.ForwardRef` and :class:`~python:typing.Type`
references to built-in types.
