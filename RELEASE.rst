RELEASE_TYPE: patch

This is a refactoring release that hopefully shouldn't have much user visible
effect. It changes how Hypothesis handles shrinking when there are multiple
failures to report. It may in some cases change which examples are found or
how fast it finds them, but the effect is unlikely to be noticeable.
