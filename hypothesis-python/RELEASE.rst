RELEASE_TYPE: minor

This release adds :class:`~hypothesis.database.GitHubArtifactDatabase`, which allows to set up example databases backed
by Github Actions artifacts. These can be used by developers to access the examples being found
continuously by a CI workflow running under GitHub Actions.

Thanks to Agustín Covarrubias for this feature!
