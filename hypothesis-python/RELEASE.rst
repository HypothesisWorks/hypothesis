RELEASE_TYPE: minor

This patch teaches the :func:`~hypothesis.extra.ghostwriter.magic` ghostwriter
to recognise "en/de" function roundtrips other than the common encode/decode
pattern, such as encrypt/decrypt or, encipher/decipher.
