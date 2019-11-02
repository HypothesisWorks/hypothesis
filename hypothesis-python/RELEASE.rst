RELEASE_TYPE: patch

This patch ensures that we only add profile information to the pytest header
if running either pytest or Hypothesis in verbose mode, matching the
`builtin cache plugin <https://docs.pytest.org/en/latest/cache.html>`__
(:issue:`2155`).
