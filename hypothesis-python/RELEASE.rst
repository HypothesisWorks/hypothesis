RELEASE_TYPE: patch

This patch fixes a rare bug where we could incorrectly treat
:obj:`~python:inspect.Parameter.empty` as a type annotation,
if the callable had an explicitly assigned ``__signature__``.
