RELEASE_TYPE: minor

The standard library :mod:`ipaddress` module is new in Python 3, and this release
adds the new :func:`~hypothesis.strategies.ip_addresses` strategy to generate
:class:`~python:ipaddress.IPv4Address`\ es and/or
:class:`~python:ipaddress.IPv6Address`\ es (depending on the ``v`` and ``network``
arguments).

If you use them in type annotations, :func:`~hypothesis.strategies.from_type` now
has strategies registered for :mod:`ipaddress` address, network, and interface types.

The provisional strategies for IP address strings are therefore deprecated.
