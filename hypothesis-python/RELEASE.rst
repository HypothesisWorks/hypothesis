RELEASE_TYPE: minor

This patch deprecates ``min_len`` or ``max_len`` of 0 in
:func:`~hypothesis.extra.numpy.byte_string_dtypes` and
:func:`~hypothesis.extra.numpy.unicode_string_dtypes`.
The lower limit is now 1.

Numpy uses a length of 0 in these dtypes to indicate an undetermined size,
chosen from the data at array creation.
However, as the :func:`~hypothesis.extra.numpy.arrays` strategy creates arrays
before filling them, strings were truncated to 1 byte.
