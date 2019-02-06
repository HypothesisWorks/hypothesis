RELEASE_TYPE: patch

This release standardises all of the shrinker's internal operations on running in a random order.

The main effect you will see from this that it should now be much less common for the shrinker to stall for a long time before making further progress.
In some cases this will correspond to shrinking more slowly, but on average it should result in faster shrinking.
