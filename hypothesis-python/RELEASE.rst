RELEASE_TYPE: patch

This patch makes :func:`~xps.arrays()` from the
:ref:`Array API extra <array-api>` slightly faster by not repeating internal
checks done on generated elements.
