RELEASE_TYPE: patch

:func:`~hypothesis.interal.compat.get_type_hints` now accepts any hints present
in `thing.__signature__`, not just instances of `type`. This allows for the use
of types from the `typing` module.
