RELEASE_TYPE: patch

Remove a case where Hypothesis would interact with the global |random.Random| instance if Hypothesis internals were used directly.
