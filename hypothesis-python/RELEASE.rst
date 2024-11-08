RELEASE_TYPE: minor

The :func:`~hypothesis.provisional.urls` strategy no longer generates
URLs where the port number is 0.

This change is motivated by the idea that the generated URLs should, at least in
theory, be possible to fetch. The port number 0 is special; if a server binds to
port 0, the kernel will allocate an unused, and non-zero, port instead. That
means that it's not possible for a server to actually be listening on port 0.
This motivation is briefly described in the documentation for
:func:`~hypothesis.provisional.urls`.

Fixes :issue:`4157`.

Thanks to @gmacon for this contribution!
