RELEASE_TYPE: minor

The :doc:`Hypothesis example database <database>` now uses a new internal format to store examples. This new format is not compatible with the previous format, so stored entries will not carry over.

The database is best thought of as a cache that may be invalidated at times. Instead of relying on it for correctness, we recommend using :obj:`@example <hypothesis.example>` to specify explicit examples. When using databases across environments (such as connecting a :class:`~hypothesis.database.GitHubArtifactDatabase` database in CI to your local environment), we recommend using the same version of Hypothesis for each where possible, for maximum reproducibility.
