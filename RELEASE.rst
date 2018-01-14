RELEASE_TYPE: patch

This change adds some additional structural information that Hypothesis will
use to guide its search.

You mostly shouldn't see much difference from this. The two most likely effects
you would notice are:

1. Hypothesis stores slightly more examples in its database for passing tests.
2. Hypothesis *may* find new bugs that it was previously missing, but it
   probably won't (this is a basic implementation of the feature that is
   intended to support future work. Although it is useful on its own, it's not
   *very* useful on its own).
