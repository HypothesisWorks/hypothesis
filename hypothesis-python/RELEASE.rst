RELEASE_TYPE: patch

Our pytest plugin now emits a warning if you set Pytest's ``norecursedirs``
config option in such a way that the ``.hypothesis`` directory would be
searched for tests.  This reliably indicates that you've made a mistake
which slows down test collection, usually assuming that your configuration
extends the set of ignored patterns when it actually replaces them.
(:issue:`4200`)
