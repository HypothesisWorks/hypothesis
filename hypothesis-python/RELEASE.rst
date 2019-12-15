RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.strategies.from_type` with
:class:`python:typing.Hashable` and :class:`python:typing.Sized`,
which previously failed with an internal error on Python 3.7 or later.

Thanks to Lea Provenzano for both reporting :issue:`2272`
and writing the patch!
