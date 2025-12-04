RELEASE_TYPE: patch

When multiple explicit |@example| decorators fail with the same error,
Hypothesis now shows only the simplest failing example (by shortlex order)
with a note about how many other examples also failed (:issue:`4520`).

To see all failing examples, use |Verbosity.verbose| or higher.
