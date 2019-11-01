RELEASE_TYPE: patch

This release fixes a bug (:issue:`2166`) where a Unicode character info
cache file was generated but never used on subsequent test runs, causing tests
to run more slowly than they should have.

Thanks to Robert Knight for this bugfix!
