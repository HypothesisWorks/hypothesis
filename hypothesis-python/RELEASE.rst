RELEASE_TYPE: patch

Disable health checks during database replay, to avoid spurious
errors when wrong examples are used due to database key collissions.
