RELEASE_TYPE: patch

This change ensures that the correct error (InvalidArgument) is raised when
we attempt to call :func:`~hypothesis.strategies.from_type` on an empty 
:class:`python:enum.Enum`.

Thanks to Paul Amazona (@whatevergeek) for writing this patch at the 
PyCon Australia sprints! - @Zac-HD 

