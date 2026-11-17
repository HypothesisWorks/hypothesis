RELEASE_TYPE: patch

This patch speeds up shrinking by comparing a candidate against the current
shrink target lazily, instead of computing the sort key of every choice on
each attempt.

It also makes finding timezone transitions for
:func:`~hypothesis.strategies.datetimes` about 30% faster, by calling
``tz.fromutc()`` directly instead of converting through UTC first.
