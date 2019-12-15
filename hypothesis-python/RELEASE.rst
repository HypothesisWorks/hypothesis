RELEASE_TYPE: patch

This patch fixes :issue:`2257`, where :func:`~hypothesis.strategies.from_type`
could incorrectly generate bytestrings when passed a generic
:class:`python:typing.Sequence` such as ``Sequence[set]``.
