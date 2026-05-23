RELEASE_TYPE: patch

This patch renames our source code directory from ``hypothesis-python`` to ``hypothesis``, and changes our canonical scheme for git tags from ``hypothesis-python-X.Y.Z`` to ``vX.Y.Z``.

We have backfilled git tags in the new ``vX.Y.Z`` scheme. Any distributions or build scripts which rely on the git tag scheme should update to the new scheme.
