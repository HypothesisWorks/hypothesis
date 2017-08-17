RELEASE_TYPE: patch

This is a bugfix release for :func:`~hypothesis.strategies.decimals`
with the ``places`` argument.

- No longer fails health checks (:issue:`725`, due to internal filtering)
- Specifying a ``min_value`` and ``max_value`` without any decimals with
  ``places`` places between them gives a more useful error message.
- Works for any valid arguments, regardless of the decimal precision context.
