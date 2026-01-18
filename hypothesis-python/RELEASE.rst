RELEASE_TYPE: patch

This patch makes Hypothesis more tolerant of slow-to-satisfy ``assume()`` calls.
Previously, Hypothesis would give up after ``max_examples * 10`` attempts; now it
uses a statistical test to stop only when 99% confident that <1% of examples
would pass (:issue:`4623`).

Thanks to @ajdavis for this improvement!
