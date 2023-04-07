RELEASE_TYPE: minor

This release adds :class:`~hypothesis.database.GitHubArtifactDatabase`, a new database
backend that allows developers to access the examples found by a Github Actions CI job.
This is particularly useful for workflows that involve continuous fuzzing,
like `HypoFuzz <https://hypofuzz.com/>`__.

Thanks to Agustín Covarrubias for this feature!
