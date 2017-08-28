RELEASE_TYPE: patch

Hypothesis now transparently handles problems with an internal unicode cache,
including file truncation or read-only filesystems (:issue:`767`).
Thanks to Sam Hames for the patch.
