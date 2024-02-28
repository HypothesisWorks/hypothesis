RELEASE_TYPE: patch

This release adds support for the Array API's `2023.12 release
<https://data-apis.org/array-api/2023.12/>`_ via the ``api_version`` argument in
:func:`~hypothesis.extra.array_api.make_strategies_namespace`. There is no
distinction between a ``2012.12`` and ``2023.12`` strategies namespace.