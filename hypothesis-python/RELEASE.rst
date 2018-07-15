RELEASE_TYPE: patch

This release deprecates the use of ``.example()`` on a strategy when running
outside an interactive REPL.

This method is only for interactive exploration of the API, not for serious
testing.  In particular, the distribution of examples doesn't match that
provided by ``@given``, and deliberately omits some examples.
