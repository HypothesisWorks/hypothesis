RELEASE_TYPE: patch

This release makes some small optimisations to our use of coverage that should
reduce constant per-example overhead. This is probably only noticeable on
examples where the test itself is quite fast. On no-op tests that don't test
anything you may see up to a fourfold speed increase (which is still
significantly slower than without coverage). On more realistic tests the speed
up is likely to be less than that.
