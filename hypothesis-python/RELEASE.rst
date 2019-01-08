RELEASE_TYPE: patch

This changes the order that the shrinker tries certain operations in its "emergency" phase which runs late in the process.
The new order should be better at avoiding long stalls where the shrinker is failing to make progress,
which may be helpful if you have difficult to shrink test cases.
However this will not be noticeabe in the vast majority of use cases.
