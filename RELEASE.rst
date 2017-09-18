RELEASE_TYPE: patch

This release is an internal change that affects how Hypothesis handles
calculating certain properties of strategies.

The primary effect of this is that it fixes a bug where use of
:func:`~hypothesis.deferred` could sometimes trigger an internal assertion
error. However the fix for this bug involved some moderately deep changes to
how Hypothesis handles certain constructs so you may notice some additional
knock-on effects.

In particular the way Hypothesis handles drawing data from strategies that
cannot generate any values has changed to bail out sooner than it previously
did. This may speed up certain tests, but it is unlikely to make much of a
difference in practice for tests that were not already failing with
Unsatisfiable.
