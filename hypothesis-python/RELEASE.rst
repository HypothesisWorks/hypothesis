RELEASE_TYPE: patch

This patch improves our pretty-printer for unusual numbers.

- Signalling NaNs are now represented by using the :mod:`struct` module
  to show the exact value by converting from a hexadecimal integer

- CPython `limits integer-to-string conversions
  <https://docs.python.org/3/library/stdtypes.html#integer-string-conversion-length-limitation>`__
  to mitigate DDOS attacks.  We now use hexadecimal for very large
  integers, and include underscore separators for integers with ten
  or more digits.
