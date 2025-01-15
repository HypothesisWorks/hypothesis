RELEASE_TYPE: minor

The :doc:`Hypothesis example database <database>` now uses a new internal format to store examples. The new format is not compatible with the previous format, so any old stored counterexamples will be silently discarded.

If you are replaying counterexamples using an external database such as :class:`~hypothesis.database.GitHubArtifactDatabase`, this means the counterexample must have been found after this version in the external database to successfully replay locally. In short, the Hypothesis versions of the local and remote databases should be both before or both after this version.
