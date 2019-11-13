RELEASE_TYPE: patch

This patch ensures that a KeyboardInterrupt received during example generation
is not treated as a mystery test failure but instead propagates to the top
level, not recording the interrupted generation in the conjecture data tree.
Thanks to Anne Archibald for identifying and fixing the problem.
