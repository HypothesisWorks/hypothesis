RELEASE_TYPE: minor

This release disallows using :obj:`python:typing.ClassVar`
with :func:`~hypothesis.strategies.from_type`
and :func:`~hypothesis.strategies.register_type_strategy`.

Why?
Because ``ClassVar`` can only be used during ``class`` definition.
We don't generate class attributes.

It also does not make sense as a runtime type on its own.
