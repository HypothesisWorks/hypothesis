RELEASE_TYPE: patch

This release tweaks the implementation of an internal weighted boolean
generator to be more friendly to the shrinker when the probability of False is
very low.

This will not have much user visible effect but large collections and stateful
tests may shrink more efficiently.
