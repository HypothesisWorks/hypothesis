RELEASE_TYPE: patch

This release weakens some minor functionality in the shrinker that had only
modest benefit and made its behaviour much harder to reason about.

This is unlikely to have much user visible effect, but it is possible that in
some cases shrinking may get slightly slower. It is primarily to make it easier
to work on the shrinker and pave the way for future work.
