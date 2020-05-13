RELEASE_TYPE: patch

This patch fixes an internal error in :func:`~hypothesis.strategies.from_type`
for :class:`python:typing.NamedTuple` in Python 3.9.  Thanks to Michel Salim
for reporting and fixing :issue:`2427`!
