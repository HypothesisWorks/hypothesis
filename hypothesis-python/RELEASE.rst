RELEASE_TYPE: minor

This release deprecates and disables the ``buffer_size`` setting,
which should have been treated as a private implementation detail
all along.  We recommend simply deleting this settings argument.
