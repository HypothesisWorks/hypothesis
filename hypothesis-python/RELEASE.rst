RELEASE_TYPE: patch

This patch ensures that we always close the download connection in
:class:`~hypothesis.database.GitHubArtifactDatabase`.
