RELEASE_TYPE: patch

Fix a rare race condition in |DirectoryBasedExampleDatabase.fetch|, where we might have read from a non-existent directory.
