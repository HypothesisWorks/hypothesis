RELEASE_TYPE: minor

This release adds an ``allow_subnormal`` argument to the
:func:`~hypothesis.strategies.floats` strategy, which can explicitly toggle the
generation of :wikipedia:`subnormal floats <Subnormal_number>` (:issue:`3155`).
Disabling such generation is useful when testing flush-to-zero builds of
libraries.

:func:`nps.from_dtype() <hypothesis.extra.numpy.from_dtype>` and
:func:`xps.from_dtype` can also accept the ``allow_subnormal`` argument, and
:func:`xps.from_dtype` or :func:`xps.arrays` will disable subnormals by default
if the array module ``xp`` is detected to flush-to-zero (like is typical with
CuPy).
