RELEASE_TYPE: patch

This release fixes :issue:`1864`, where some simple tests would perform very slowly,
because they would run many times with each subsequent run being progressively slower.
They will now stop after a more reasonable number of runs without hitting this problem.

Unless you are hitting exactly this issue, it is unlikely that this release will have any effect,
but certain classes of custom generators that are currently very slow may become a bit faster,
or start to trigger health check failures.
