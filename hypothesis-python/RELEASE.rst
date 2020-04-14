RELEASE_TYPE: patch

This release (potentially very significantly) improves the performance of failing tests in some rare cases,
mostly only relevant when using :ref:`targeted property-based testing <targeted-search>`,
by stopping further optimisation of unrelated test cases once a failing example is found.
