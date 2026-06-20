RELEASE_TYPE: patch

This patch fixes a thread-safety bug where concurrent use of the same strategy instance could error in rare cases. (:issue:`4475`).
