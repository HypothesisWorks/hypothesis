RELEASE_TYPE: minor

:func:`~hypothesis.strategies.from_type` can now handle constructors with
required positional-only arguments if they have type annotations.  Previously,
we only passed arguments by keyword.
