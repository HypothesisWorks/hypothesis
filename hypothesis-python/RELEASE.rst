RELEASE_TYPE: patch

This patch ensures that a KeyboardInterrupt received during example generation
is not treated as a mystery test failure but instead propagates to the top
level.
