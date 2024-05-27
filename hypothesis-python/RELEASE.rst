RELEASE_TYPE: minor

This release migrates the shrinker to our new internal representation, called the IR layer (:pull:`3962`). This improves the shrinker's performance in the majority of cases. For example, on the Hypothesis test suite, shrinking is a median of 1.38x faster.

It is possible this release regresses performance while shrinking certain strategies. If you encounter strategies which reliably shrink more slowly than they used to (or shrink slowly at all), please open an issue!

You can read more about the IR layer at :issue:`3921`.
