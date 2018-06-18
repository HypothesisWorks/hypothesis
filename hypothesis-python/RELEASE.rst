RELEASE_TYPE: patch

This adds support for partially sorting examples which cannot be fully sorted.
For example, [5, 4, 3, 2, 1, 0] with a constraint that the first element needs
to be larger than the last becomes [1, 2, 3, 4, 5, 0].

Thanks to Luke for contributing.
