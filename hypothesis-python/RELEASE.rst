RELEASE_TYPE: minor

Adds ability to specify hypothesis strategies in :obj:`python:typing.Annotated`.
Example: ``PositiveInt = Annotated[int, st.integer(min_value=1)]``
