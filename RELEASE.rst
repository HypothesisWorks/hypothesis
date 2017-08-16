RELEASE_TYPE: patch

This release should improve the performance of some tests which
experienced a slow down as a result of the 3.13.0 release.

Tests most likely to benefit from this are ones that make extensive
use of `min_size` parameters, but others may see some improvement
as well.
