RELEASE_TYPE: patch

This patch makes writes to the cache of constants collected from local source
files atomic. Previously, a concurrent process sharing the same ``.hypothesis``
directory, such as another :pypi:`pytest-xdist` worker, could read a partially
written cache file, which silently changed the data generated for a given
:func:`@seed <hypothesis.seed>` (:issue:`4885`).
