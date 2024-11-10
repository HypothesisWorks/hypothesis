RELEASE_TYPE: patch

This patch avoids computing some string representations we won't need,
giving a small speedup (part of :issue:`4139`).
