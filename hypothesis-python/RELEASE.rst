RELEASE_TYPE: patch

This release changes how the shrinker handles reordering examples within
a failing test case.

This is primarily an efficiency improvement, and should result in significant
improvements to shrinking speed in large examples. You may also see some changes
in example quality, but they should generally be improvements and are likely
minor at best.
