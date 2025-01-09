RELEASE_TYPE: patch

:class:`~hypothesis.database.DirectoryBasedExampleDatabase` now creates files representing database entries atomically, avoiding a very brief intermediary state where a file could be created but not yet written to.
