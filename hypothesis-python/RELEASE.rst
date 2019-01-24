RELEASE_TYPE: patch

This release changes Hypothesis's internal approach to caching the results of executing test cases.
The result should be that it is now significantly less memory hungry, especially when shrinking large test cases.

Some tests may get slower or faster depending on whether the new or old caching strategy was well suited to them,
but any change in speed in either direction should be minor.
