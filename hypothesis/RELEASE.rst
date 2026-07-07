RELEASE_TYPE: patch

This patch fixes a ``KeyError`` in |GitHubArtifactDatabase| when reading an
artifact whose zip file contains no explicit directory entries, which is the
case for zips produced by ``actions/upload-artifact``.
