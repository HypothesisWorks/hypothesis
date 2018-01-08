RELEASE_TYPE: patch

This release fixes a bug in the shrinker that prevented the optimisations in
3.44.6 from working in some cases. It would not have worked correctly when
filtered examples were nested (e.g. with a set of integers in some range).

This would not have resulted in any correctness problems, but shrinking may
have been slower than it otherwise could be.
