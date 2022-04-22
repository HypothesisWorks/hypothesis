RELEASE_TYPE: minor

This release updates :func:`xps.indices` by introducing an ``allow_newaxis``
argument, defaulting to ``False``. If ``allow_newaxis=True``, indices can be
generated that add dimensions to arrays, which is achieved by the indexer
containing ``None``. This change is to support a specification change that
expand dimensions via indexing (`data-apis/array-api#408
<https://github.com/data-apis/array-api/pull/408>`_).
