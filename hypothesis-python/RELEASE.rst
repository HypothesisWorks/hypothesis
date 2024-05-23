RELEASE_TYPE: patch

This patch fixes one of our shrinking passes getting into a rare ``O(n)`` case instead of ``O(log(n))``.
