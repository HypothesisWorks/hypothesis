RELEASE_TYPE: minor

This release emits a warning if you use the ``.example()`` method of
a strategy in a non-interactive context.

:func:`~hypothesis.given` is a much better choice for writing tests,
whether you care about performance, minimal examples, reproducing
failures, or even just the variety of inputs that will be tested!
