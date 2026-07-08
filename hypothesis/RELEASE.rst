RELEASE_TYPE: patch

This patch fixes |GitHubArtifactDatabase| to drop the ``Authorization`` header
when GitHub redirects an artifact download to a presigned storage URL on a
different host.  The bearer token is only required for ``api.github.com``, and
forwarding it across the redirect caused the presigned URL to reject the
download with a ``401``.
