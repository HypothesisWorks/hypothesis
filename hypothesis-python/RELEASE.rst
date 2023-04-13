RELEASE_TYPE: minor

This release deprecates ``Healthcheck.all()``, and :ref:`adds a codemod <codemods>`
to automatically replace it with ``list(Healthcheck)`` (:issue:`3596`).