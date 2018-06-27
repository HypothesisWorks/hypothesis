RELEASE_TYPE: patch

This patch fixes type-checking errors in our vendored prety-printer,
which were ignored by our mypy config but visible for anyone else
(whoops).  Thanks to Pi Delport for reporting :issue:`1359` so promptly.
