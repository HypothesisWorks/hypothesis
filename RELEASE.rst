RELEASE_TYPE: patch

This is a bugfix release:

- :func:`~hypothesis.strategies.builds` would try to infer a strategy for
  required positional arguments of the target from type hints, even if they
  had been given to :func:`~hypothesis.strategies.builds` as positional
  arguments (:issue:`946`).  Now it only infers missing required arguments.
- An internal introspection function wrongly reported ``self`` as a required
  argument for bound methods, which might also have affected
  :func:`~hypothesis.strategies.builds`.  Now it knows better.
