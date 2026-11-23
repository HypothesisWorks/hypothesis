RELEASE_TYPE: patch

This patch makes collecting constants from local modules faster when many
test modules are imported, by recognising test files from their path before
resolving it on disk (:issue:`4978`).
