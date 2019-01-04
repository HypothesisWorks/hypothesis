RELEASE_TYPE: patch

This release fixes a bug where certain places Hypothesis internal errors could be
raised during shrinking when a user exception occurred that suppressed an exception
Hypothesis uses internally in its generation.

The two known ways to trigger this problem were:

* Errors raised in stateful tests' teardown function.
* Errors raised in finally blocks that wrapped a call to ``data.draw``.

These cases will now be handled correctly.
