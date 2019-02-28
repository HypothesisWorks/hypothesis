RELEASE_TYPE: patch

This release makes some micro-optimisations to certain calculations performed in the shrinker.
These should particularly speed up large test cases where the shrinker makes many small changes.
It will also reduce the amount allocated, but most of this is garbage that would have been immediately thrown away,
so you probably won't see much effect specifically from that.
