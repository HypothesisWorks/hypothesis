RELEASE_TYPE: patch

This patch updates :func:`xps.indices` so no flat indices are generated, i.e.
generated indices will now always explicitly cover each axes of an array if no
ellipsis is present. This is to be consistent with a specification change that
dropped support for flat indexing
(`#272 <https://github.com/data-apis/array-api/pull/272>`_).
