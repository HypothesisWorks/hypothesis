RELEASE_TYPE: patch

This release changes Hypothesis's internal representation of a test case to calculate some expensive structural information on demand rather than eagerly.
This should reduce memory usage a fair bit, and may make generation somewhat faster.
