RELEASE_TYPE: patch

:func:`~hypothesis.strategies.from_type` no longer raises
``decimal.InvalidOperation`` for ``Annotated[Decimal, ...]`` with a
``Gt``, ``Ge``, ``Lt``, ``Le`` or ``Interval`` constraint from
:pypi:`annotated-types`.  NaN can never satisfy such a bound, so it is no
longer generated there.
