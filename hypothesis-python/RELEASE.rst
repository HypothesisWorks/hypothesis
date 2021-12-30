RELEASE_TYPE: minor

This release disallows using :obj:`python:typing.TypeAlias`
with :func:`~hypothesis.strategies.from_type`
and :func:`~hypothesis.strategies.register_type_strategy`.

Why? Because ``TypeAlias`` is not really a type,
it is a tag for type checkers that some expression is a type alias,
not something else.

It does not make sense for Hypothesis to resolve it as a strategy.
References :issue:`2978`.
