RELEASE_TYPE: patch

This release reduces the delay when generating text for the first time in
a test run if no Unicode character map cache exists (:issue:`2170`), which could
lead to timeouts with the default ``deadline`` setting.

Thanks to Robert Knight for this patch!
