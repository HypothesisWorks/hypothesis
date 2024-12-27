RELEASE_TYPE: patch

The shrinker now uses the `typed choice sequence` (:issue:`3921`) to determine counterexample complexity. We expect this to mostly match the previous ordering, but it may result in reporting different counterexamples in some cases.
