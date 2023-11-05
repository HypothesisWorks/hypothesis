RELEASE_TYPE: patch

This patch refactors ``from_type(typing.Tuple)``, allowing
:func:`~hypothesis.strategies.register_type_strategy` to take effect
for tuples instead of being silently ignored (:issue:`3750`).

Thanks to Nick Collins for reporting and extensive work on this issue.
