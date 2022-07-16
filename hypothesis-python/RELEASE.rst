RELEASE_TYPE: patch

This patch adds a bit of functionality to automatic refactoring of simple filters. Specifically, it adds handling for requests for nonfinite floats and ints (using math.isfinite, math.isinf, and math.isnan).

Also reworks tests for filter rewriting slightly to test new functionality, and to separate cases where the rewrite should return an empty strategy from cases where the rewrite should return a strategy that always fails.