RELEASE_TYPE: minor

This release removes support for Python 3.5.0 and 3.5.1, where the
:mod:`python:typing` module was quite immature (e.g. missing
:func:`~python:typing.overload` and :obj:`~python:typing.Type`).

Note that Python 3.5 will reach its end-of-life in September 2020,
and new releases of Hypothesis may drop support somewhat earlier.

.. note::
    ``pip install hypothesis`` should continue to give you the latest compatible version.
    If you have somehow ended up with an incompatible version, you need to update your
    packaging stack to ``pip >= 9.0`` and ``setuptools >= 24.2`` - see `here for details
    <https://packaging.python.org/guides/distributing-packages-using-setuptools/#python-requires>`__.
    Then ``pip uninstall hypothesis && pip install hypothesis`` will get you back to
    a compatible version.
