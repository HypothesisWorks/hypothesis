RELEASE_TYPE: patch

This patch allows :func:`~hypothesis.strategies.from_type` to handle the
empty tuple type, :obj:`typing.Tuple[()] <python:typing.Tuple>`.
