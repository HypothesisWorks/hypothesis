RELEASE_TYPE: patch

This patch fixes :issue:`3169`, an extremely rare bug which would
trigger if an internal least-recently-reused cache dropped a newly
added entry immediately after it was added.
