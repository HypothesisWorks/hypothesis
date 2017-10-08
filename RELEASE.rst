RELEASE_TYPE: patch

:func:`~hypothesis.strategies.from_type` failed with a very confusing error
if passed a :func:`~python:typing.NewType` (:issue:`901`).  These psudeo-types
are now unwrapped correctly, and strategy inference works as expected.
