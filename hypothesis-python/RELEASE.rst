RELEASE_TYPE: minor

This release updates :func:`~hypothesis.extra.array_api.make_strategies_namespace`
by introducing a ``api_version`` argument, defaulting to ``None``. If a `valid
version string <https://data-apis.org/array-api/latest/future_API_evolution.html#versioning>`_,
the returned strategies namespace should conform to the specified version. If
``None``, the version of the passed Array API module ``xp`` is inferred and
conformed to.

This release also introduces :func:`xps.real_dtypes`, which generates
all real-valued dtypes (i.e. integers and floats) specified in the Array API.
