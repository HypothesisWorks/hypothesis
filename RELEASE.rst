RELEASE_TYPE: patch

This release makes two changes:

* It makes the calculation of some of the metadata that Hypothesis uses for
  shrinking occur lazily. This should speed up performance of test case
  generation a bit because it no longer calculates information it doesn't need.
* It improves the shrinker for certain classes of nested examples. e.g. when
  shrinking lists of lists, the shrinker is now able to concatenate two
  adjacent lists together into a single list. As a result of this change,
  shrinking may get somewhat slower when the minimal example found is large.
