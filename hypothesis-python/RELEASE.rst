RELEASE_TYPE: minor

This release allows :func:`~hypothesis.extra.numpy.from_dtype` to generate
Unicode strings which cannot be encoded in UTF-8, but are valid in Numpy
arrays (which use UTF-32).

This logic will only be used with :pypi:`Numpy` >= 1.19, because earlier
versions have `an issue <https://github.com/numpy/numpy/issues/15363>`__
which led us to revert :ref:`Hypothesis 5.2 <v5.2.0>` last time!
