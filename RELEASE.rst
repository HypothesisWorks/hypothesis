RELEASE_TYPE: patch

This patch fixes :issue:`2272`, where inferring a 
inferring a strategy based for :class:`python:typing.Hashable`
or  :class:`python:typing.Sized` failed unexpectedly when
trying to tried to access an empty `__args__` tuple.
We now adress these collections.abc alias types more explicitly.