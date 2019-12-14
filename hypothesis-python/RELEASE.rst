RELEASE_TYPE: minor

This release adds database support for :ref:`targeted property-based testing <targeted-search>`,
so the best examples based on the targeting will be saved and reused between runs.
This is mostly laying groundwork for future features in this area, but
will also make targeted property based tests more useful during development,
where the same tests tend to get run over and over again.

This release also adds a dependency on the ``sortedcontainers`` package.
