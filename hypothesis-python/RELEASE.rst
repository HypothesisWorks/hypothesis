RELEASE_TYPE: patch

This release removes two shrink passes that Hypothesis runs late in the process.
These were very expensive when the test function was slow and often didn't do anything useful.

Shrinking should get faster for most failing tests.
If you see any regression in example quality as a result of this release, please let us know.
