RELEASE_TYPE: patch

"Bug fixes and performance improvements".

This release is a fairly major overhaul of the shrinker designed to improve
its behaviour on large examples, especially around stateful testing. You
should hopefully see shrinking become much faster, with little to no quality
degradation (in some cases quality may even improve).
