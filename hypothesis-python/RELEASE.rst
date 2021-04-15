RELEASE_TYPE: patch

This release improves the :doc:`Ghostwriter's <ghostwriter>` handling
of exceptions, by reading ``:raises ...:`` entries in function docstrings
and ensuring that we don't suppresss the error raised by test assertions.
