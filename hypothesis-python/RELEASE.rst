RELEASE_TYPE: minor

This release adds support for the Array API's `2022.12 release
<https://data-apis.org/array-api/2022.12/>`_ via the ``api_version`` argument in
:func:`~hypothesis.extra.array_api.make_strategies_namespace`. Concretely this
involves complex support in its existing strategies, plus an introduced
:func:`xps.complex_dtypes` strategy.

Additionally this release now treats :ref:`hypothesis.extra.array_api
<array-api>` as stable, meaning breaking changes should only happen with major
releases of Hypothesis.
