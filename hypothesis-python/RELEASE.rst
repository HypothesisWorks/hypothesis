RELEASE_TYPE: patch

This patch updates internal testing for the :ref:`Array API extra <array-api>`
to be consistent with new specification changes: ``sum()`` not accepting
boolean arrays (`#234 <https://github.com/data-apis/array-api/pull/234>`_),
``unique()`` split into separate functions
(`#275 <https://github.com/data-apis/array-api/pull/275>`_), and treating NaNs
as distinct (`#310 <https://github.com/data-apis/array-api/pull/310>`_). It has
no user visible impact.
