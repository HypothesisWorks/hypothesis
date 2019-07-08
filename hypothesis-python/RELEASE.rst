RELEASE_TYPE: patch

This release changes how the shrinker represents its progress internally. For large generated test cases
this should result in significantly less memory usage and possibly faster shrinking. Small generated
test cases may be slightly slower to shrink but this shouldn't be very noticeable.
