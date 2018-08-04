RELEASE_TYPE: patch

This release improves the efficiency of how the shrinker reorders examples, by
significantly limiting the set of transformations it will try. You may see some
degradation in example quality (if you do, please tell us!) but mostly you
should see much faster shrinking.
