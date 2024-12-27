RELEASE_TYPE: patch

The shrinker now uses the typed choice sequence (:issue:`3921`) when ordering failing examples. As a result, Hypothesis may now report a different minimal failing example for some tests. We expect most cases to remain unchanged.
