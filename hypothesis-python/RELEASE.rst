RELEASE_TYPE: patch

This patch handles passing an empty :class:`python:enum.Enum` to
:func:`~hypothesis.strategies.from_type` returns 
:func:`~hypothesis.strategies.nothing`, instead of raising an 
internal :class:`python:AssertionError`.

Thanks to Paul Amazona (@whatevergeek) for writing this patch at the 
PyCon Australia sprints!

