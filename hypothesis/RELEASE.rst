RELEASE_TYPE: patch

Now that we combine coverage data across our CI jobs (:issue:`4261`), this patch
removes around a hundred ``# pragma: no cover`` comments which are no longer
needed, and expands our 100%-coverage requirement to several previously-omitted
files.

The ``explain`` phase no longer reports lines inside the standard library,
which were occasionally included in (and made for misleading) explanations.

The constants-collection feature introduced in :ref:`version 6.131.1 <v6.131.1>`
now also collects the float components of complex literals like ``3.5j``.
