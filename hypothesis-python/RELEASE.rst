RELEASE_TYPE: minor

New input validation for :func:`~hypothesis.strategies.recursive`
will raise an error rather than hanging indefinitely if passed
invalid ``max_leaves=`` arguments.
