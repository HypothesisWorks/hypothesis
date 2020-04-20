RELEASE_TYPE: patch

This release reverses the order in which some operations are tried during shrinking.
This should generally be a slight performance improvement, but most tests are unlikely to notice much difference.
