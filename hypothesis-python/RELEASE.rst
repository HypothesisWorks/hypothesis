RELEASE_TYPE: patch

This release randomizes the order in which the shrinker tries some of its initial normalization operations.
You are unlikely to see much difference as a result unless your generated examples are very large.
In this case you may see some performance improvements in shrinking.
