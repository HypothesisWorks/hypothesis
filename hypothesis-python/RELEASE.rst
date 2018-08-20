RELEASE_TYPE: minor

This release improves argument validation for stateful testing.

- If the target or targets of a :func:`~hypothesis.stateful.rule` are invalid,
  we now raise a useful validation error rather than an internal exception.
- Passing both the ``target`` and ``targets`` arguments is deprecated -
  append the ``target`` bundle to the ``targets`` tuple of bundles instead.
- Passing the name of a Bundle rather than the Bundle itself is also deprecated.
