RELEASE_TYPE: patch

This patch wraps some internal helper code in our proxies decorator to prevent
mutations of method docstrings carrying over to other instances of the respective
methods.
