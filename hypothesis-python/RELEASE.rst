RELEASE_TYPE: minor

In preparation for `future versions of the Array API standard
<https://data-apis.org/array-api/latest/future_API_evolution.html>`__,
:func:`~hypothesis.extra.array_api.make_strategies_namespace` now accepts an
optional ``api_version`` argument, which determines the version conformed to by
the returned strategies namespace. If ``None``, the version of the passed array
module ``xp`` is inferred.

This release also introduces :func:`xps.real_dtypes`. This is currently
equivalent to the existing :func:`xps.numeric_dtypes` strategy, but exists
because the latter is expected to include complex numbers in the next version of
the standard.
