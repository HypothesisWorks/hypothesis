RELEASE_TYPE: patch

Now that we combine coverage data across our CI jobs (:issue:`4261`), this patch
removes around a hundred ``# pragma: no cover`` comments which are no longer
needed, and expands our 100%-coverage requirement to several previously-omitted
files. There is no user-visible change.
