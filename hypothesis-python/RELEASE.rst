RELEASE_TYPE: minor

This release teaches :func:`~hypothesis.strategies.from_type` a neat trick:
when resolving an :obj:`python:typing.Annotated` type, if one of the annotations
is a strategy object we use that as the inferred strategy.  For example:

.. code-block:: python

    PositiveInt = Annotated[int, st.integers(min_value=1)]

If there are multiple strategies, we use the last outer-most annotation.
See :issue:`2978` and :pull:`3082` for discussion.

*Requires Python 3.9 or later for*
:func:`get_type_hints(..., include_extras=False) <typing.get_type_hints>`.
