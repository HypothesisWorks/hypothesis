RELEASE_TYPE: patch

This release fixes a problem that was introduced in `3.56.0 <v3.56.0>`:
Use of the ``HYPOTHESIS_VERBOSITY_LEVEL`` environment variable was, rather
than deprecated, actually broken due to being read before various setup 
the deprecation path needed was done. It now works correctly (and emits a
deprecation warning).
