RELEASE_TYPE: patch

In preparation for supporting JAX in :ref:`hypothesis.extra.array_api <array-api>`,
this release supports immutable arrays being generated via :func:`xps.arrays`.
In particular, we internally removed an instance of in-place array modification,
which isn't possible for an immutable array.
