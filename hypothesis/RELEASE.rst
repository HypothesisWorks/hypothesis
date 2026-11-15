RELEASE_TYPE: patch

This patch makes finding timezone transitions for
:func:`~hypothesis.strategies.datetimes` about 30% faster, by calling
``tz.fromutc()`` directly instead of converting through UTC first.
