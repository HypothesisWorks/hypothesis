RELEASE_TYPE: patch

This release removes some functionality from the shrinker that was taking a
considerable amount of time and does not appear to be useful any more due to
a number of quality improvements in the shrinker.

You may see some degradation in shrink quality as a result of this, but mostly
shrinking should just get much faster.
