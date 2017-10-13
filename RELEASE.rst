RELEASE_TYPE: patch

This patch has two improvements for strategies based on enumerations.

- :func:`~hypothesis.strategies.from_type` now handles enumerations correctly,
  delegating to :func:`~hypothesis.strategies.sampled_from`.  Previously it
  noted that ``Enum.__init__`` has no required arguments and therefore delegated
  to :func:`~hypothesis.strategies.builds`, which would subsequently fail.
- When sampling from an :class:`python:enum.Flag`, we also generate combinations
  of members. Eg for ``Flag('Permissions', 'READ, WRITE, EXECUTE')`` we can now
  generate, ``Permissions.READ``, ``Permissions.READ|WRITE``, and so on.
