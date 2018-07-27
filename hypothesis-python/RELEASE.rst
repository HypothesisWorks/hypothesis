RELEASE_TYPE: patch

This release changes how Hypothesis deletes data when shrinking in order to
better handle deletion of large numbers of contiguous sequences. Most tests
should see little change, but this will hopefully provide a significant
speed up for :doc:`stateful testing <stateful>`.
