RELEASE_TYPE: patch

Calling ``.map()`` or ``.flatmap()`` on :func:`~hypothesis.strategies.data`
with a keyword argument now raises the intended error explaining that this is
not supported, instead of a generic error about an unexpected keyword argument.
