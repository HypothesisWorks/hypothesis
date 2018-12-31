RELEASE_TYPE: patch

This release changes the order that the shrinker tries to delete data in.
For large and slow tests this may significantly improve the performance of shrinking.
