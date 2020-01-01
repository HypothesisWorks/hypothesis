RELEASE_TYPE: minor

This release teaches :func:`~hypothesis.strategies.from_type` how to generate
:class:`python:datetime.timezone`.  As a result, you can now generate
:class:`python:datetime.tzinfo` objects without having :pypi:`pytz` installed.

If your tests specifically require :pypi:`pytz` timezones, you should be using
:func:`hypothesis.extra.pytz.timezones` instead of ``st.from_type(tzinfo)``.
