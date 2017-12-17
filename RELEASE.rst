RELEASE_TYPE: patch

This release fixes a bug with Hypothesis's database management - examples that
were found in the course of shrinking were saved in a way that indicated that
they had distinct causes, and so they would all be retried on the start of the
next test. The intended behaviour, which is now what is implemented, is that
only a bounded subset of these examples would be retried.
