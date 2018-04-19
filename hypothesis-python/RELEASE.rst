RELEASE_TYPE: patch

This release fixes a problem introduced in `3.56.0 <v3.56.0>` where
setting the hypothesis home directory (through currently undocumented
means) would no longer result in the default database location living
in the new home directory.
