RELEASE_TYPE: patch

This patch fixes inference in the :func:`~hypothesis.strategies.builds`
strategy with subtypes of :class:`python:typing.NamedTuple`, where the
``__init__`` method is not useful for introspection.  We now use the
field types instead - thanks to James Uther for identifying this bug.
