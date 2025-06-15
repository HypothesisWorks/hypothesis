RELEASE_TYPE: patch

Fix a rare race condition in |ExampleDatabase.fetch|, where we might have read from a non-existent directory.
