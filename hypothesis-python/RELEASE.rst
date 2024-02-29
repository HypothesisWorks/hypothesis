RELEASE_TYPE: patch

This release adds support for the Array API's `2023.12 release
<https://data-apis.org/array-api/2023.12/>`_ via the ``api_version`` argument in
:func:`~hypothesis.extra.array_api.make_strategies_namespace`. The API additions
and modifications in the ``2023.12`` spec do not necessitate any changes in the
Hypothesis strategies, hence there is no distinction between a ``2022.12`` and
``2023.12`` strategies namespace.