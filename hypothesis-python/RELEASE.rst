RELEASE_TYPE: minor

This release improves our support for datetimes and times around DST transitions.

:func:`~hypothesis.strategies.times` and :func:`~hypothesis.strategies.datetimes`
are now sometimes generated with ``fold=1``, indicating that they represent the
second occurrence of a given wall-time when clocks are set backwards.
This may be set even when there is no transition, in which case the ``fold``
value should be ignored.

For consistency, timezones provided by the :pypi:`pytz` package can now
generate imaginary times (such as the hour skipped over when clocks 'spring forward'
to daylight saving time, or during some historical timezone transitions).
All other timezones have always supported generation of imaginary times.

If you prefer the previous behaviour, :func:`~hypothesis.strategies.datetimes`
now takes an argument ``allow_imaginary`` which defaults to ``True`` but
can be set to ``False`` for any timezones strategy.
