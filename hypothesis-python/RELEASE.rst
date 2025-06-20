RELEASE_TYPE: minor

This version adds support for generating numpy.ndarray and pandas.Series with any python object as an element.
Effectively, hypothesis can now generate ``np.array([MyObject()], dtype=object)``.
The first use-case for this is with Pandas and Pandera where it is possible and sometimes required to have columns which themselves contain structured datatypes.
Pandera seems to be waiting for this change to support ``PythonDict, PythonTypedDict, PythonNamedTuple`` etc.

---

- Accept ``dtype.kind = 'O'`` in ``from_dtype``
- Use ``.iat`` instead of ``.iloc`` to set values in pandas strategies