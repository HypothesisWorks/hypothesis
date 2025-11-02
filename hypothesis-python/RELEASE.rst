RELEASE_TYPE: minor

This release adds support for :class:`~fractions.Fraction` objects as ``min_value``
and ``max_value`` bounds in :func:`~hypothesis.strategies.decimals`, if they can
be exactly represented as decimals in the target precision (:issue:`4466`).

Bounding :func:`~hypothesis.strategies.decimals` with *other* values that cannot
be exactly represented is now deprecated; previously the bounds could be off by one.
