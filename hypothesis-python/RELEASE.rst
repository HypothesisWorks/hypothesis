RELEASE_TYPE: minor

This release teaches :func:`~hypothesis.strategies.from_type` how to handle
:class:`~python:typing.ChainMap`, :class:`~python:typing.Counter`,
:class:`~python:typing.Deque`, :class:`~python:typing.Generator`,
:class:`~python:typing.Match`, :class:`~python:typing.OrderedDict`,
:class:`~python:typing.Pattern`, and :class:`python:collections.abc.Set`
(:issue:`2654`).
