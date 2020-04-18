RELEASE_TYPE: minor

This release improves our support for datetimes and times around DST transitions.

:func:`~hypothesis.strategies.times` and :func:`~hypothesis.strategies.datetimes`
are now sometimes generated with ``fold=1``, indicating that they represent the
second occurrence of a given wall-time when clocks are set backwards.
This may be set even when there is no transition, in which case the ``fold``
value should be ignored.

For consistency, timezones provided by the :pypi:`pytz` package can now
generate imaginary times.  This has always been the case for other timezones.

If you prefer the previous behaviour, :func:`~hypothesis.strategies.datetimes`
now takes an argument ``allow_imaginary`` which defaults to ``True``.
