RELEASE_TYPE: patch

This release modifies the way that Hypothesis deletes data during shrinking.
It will primarily be noticeable for very large examples, which should now shrink faster.

The shrinker is now also able to perform some deletions that it could not previously,
but this is unlikely to be very noticeable.
