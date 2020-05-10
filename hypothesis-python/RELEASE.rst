RELEASE_TYPE: minor

This release limits the maximum duration of the shrinking phase to five minutes,
so that Hypothesis does not appear to hang when making very slow progress
shrinking a failing example (:issue:`2340`).

If one of your tests triggers this logic, we would really appreciate a bug
report to help us improve the shrinker for difficult but realistic workloads.
