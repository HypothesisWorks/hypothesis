RELEASE_TYPE: minor

The standard library :mod:`ipaddress` module is new in Python 3, and this release
adds the new :func:`~hypothesis.strategies.ip_addresses` strategy to generate
:class:`~python:ipaddress.IPv4Address`\ es and/or
:class:`~python:ipaddress.IPv6Address`\ es (depending on the ``v`` and ``network``
arguments).
