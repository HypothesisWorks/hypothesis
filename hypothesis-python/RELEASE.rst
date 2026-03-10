RELEASE_TYPE: patch

When shrinking takes more than five minutes, Hypothesis now prints the
``@seed`` decorator alongside the slow-shrinking warning so you can
reproduce the failure.

Thanks to Ian Hunt-Isaak for this contribution!
