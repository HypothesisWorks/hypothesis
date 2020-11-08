RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.provisional.urls` strategy ensuring that
`~` (tilde) is treated as one of the url-safe characters (:issue:`2658`).

