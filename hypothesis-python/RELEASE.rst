RELEASE_TYPE: minor

This release adds new :func:`~hypothesis.strategies.timezones` and
:func:`~hypothesis.strategies.timezone_keys` strategies (:issue:`2630`)
based on the new :mod:`python:zoneinfo` module in Python 3.9.

``pip install hypothesis[zoneinfo]`` will ensure that you have the
appropriate backports installed if you need them.
