RELEASE_TYPE: minor

Adds a new ``codec=`` option in :func:`~hypothesis.strategies.characters`, making it
convenient to produce only characters which can be encoded as ``ascii`` or ``utf-8``
bytestrings.

Support for other codecs will be added in a future release.
