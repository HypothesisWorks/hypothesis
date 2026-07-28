RELEASE_TYPE: patch

Now that we combine coverage data across our CI jobs (:issue:`4261`), this patch
removes around a hundred ``# pragma: no cover`` comments which are no longer
needed, and expands our 100%-coverage requirement to several previously-omitted
files.

The ``explain`` phase no longer reports lines inside the standard library,
which were occasionally included in (and made for misleading) explanations.
