RELEASE_TYPE: patch

This release removes some minor functionality from the shrinker that had only
modest benefit and made its behaviour much harder to reason about.

This is unlikely to have much user visible effect, but it is possible that in
some cases shrinking may get slightly slower.
