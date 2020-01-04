RELEASE_TYPE: minor

This release allows :func:`~hypothesis.extra.numpy.from_dtype` to generate
Unicode strings which cannot be encoded in UTF-8, but are valid in Numpy
arrays (which use UTF-32).
